import asyncio
import logging
import time
import uuid
from datetime import timedelta
from urllib.parse import urlparse

from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.apps import App
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types
from sqlalchemy import func, select

from app.config import settings
from app.database import Session
from app.guide_agent.agent import root_agent
from app.guide_agent.intake import classify
from app.guide_agent.usage import UsagePlugin, summarize
from app.guide_agent.validator import NotIdentified, finalize
from app.guides import service as guides
from app.guides.models import now
from app.guides.schemas import GuideDraft
from app.runs.models import RunRow
from app.web.templating import templates

log = logging.getLogger(__name__)
APP = "oauth_guides"
STAGES = {"resolver": "Identifying the app", "review_researcher": "Researching review and approval rules",
          "oauth_researcher": "Researching OAuth technical details", "prober": "Testing OAuth endpoints live",
          "writer": "Writing the guide"}
LANES = {"resolver": "Identify", "review_researcher": "Approval", "oauth_researcher": "OAuth", "prober": "Live test",
         "writer": "Write"}
NARRATORS = {"resolver", "review_researcher", "oauth_researcher", "prober"}  # the writer outputs JSON, not prose
STREAMING = RunConfig(streaming_mode=StreamingMode.SSE)
# Fields of the writer's JSON, announced as they appear in its stream so the last stage is not silent
SECTIONS = {"headline": "Summing up difficulty and effort", "stages": "Drafting the step-by-step path",
            "requirements": "Listing requirements", "gotchas": "Collecting gotchas",
            "permissions": "Mapping permissions to scopes", "blockers": "Writing what to do when stuck",
            "key_claims": "Grading evidence", "sources": "Attaching sources"}

sessions = DatabaseSessionService(db_url=settings.db_url)
runner = Runner(app=App(name=APP, root_agent=root_agent, plugins=[UsagePlugin()]), session_service=sessions)
_events: dict[str, list[dict]] = {}  # live runs: run_id -> ordered events
_waiters: dict[str, asyncio.Event] = {}
_active: dict[str, str] = {}  # normalized query -> run_id
_tasks: dict[str, asyncio.Task] = {}


class RateLimited(Exception):
    pass


def _emit(run_id: str, event: str, **data) -> None:
    """Append one event with a sequence number so clients apply them in order and can resume."""
    events = _events[run_id]
    events.append({"seq": len(events), "event": event, "data": data})
    _waiters[run_id].set()


def _host(url: str) -> str:
    return urlparse(url).netloc.removeprefix("www.")


def _describe_call(name: str, args: dict) -> tuple[str, str, str]:
    """Return (kind, text, url) for a tool call."""
    url = args.get("url") or args.get("base_url") or args.get("authorize_url") or ""
    return {
        "search_web": ("search", f"Searching “{args.get('query', '')}”", ""),
        "fetch_page": ("read", f"Reading {_host(url)}", url),
        "check_discovery": ("probe", f"Checking discovery metadata on {_host(url)}", url),
        "probe_authorize": ("probe", f"Probing authorize endpoint on {_host(url)} with a fake client_id", url),
    }.get(name, ("tool", name, ""))


def _describe_result(name: str, resp: dict) -> dict:
    """Short result, result domains and links for a tool response."""
    if "error" in resp:
        return {"result": f"skipped: {str(resp['error'])[:80]}"}
    if name == "search_web":
        results = resp.get("results", [])
        return {"result": f"{len(results)} results", "domains": list(dict.fromkeys(_host(r["url"]) for r in results))[:6],
                "links": [{"title": r.get("title") or _host(r["url"]), "url": r["url"]} for r in results[:6]]}
    if name == "fetch_page":
        return {"result": resp.get("title") or f"HTTP {resp.get('status')}"}
    if name == "probe_authorize":
        return {"result": f"HTTP {resp.get('status')}, hints: {', '.join(resp.get('error_hints', [])) or 'none'}"}
    return {"result": "metadata found" if "authorization_endpoint" in resp else resp.get("result", "done")}


def _texts(event) -> list[str]:
    parts = event.content.parts if event.content and event.content.parts else []
    return [p.text for p in parts if p.text and not p.thought]


async def _check_limits(ip: str) -> None:
    async with Session() as db:
        hour = await db.scalar(select(func.count()).where(RunRow.client_ip == ip, RunRow.created_at > now() - timedelta(hours=1)))
        day = await db.scalar(select(func.count()).where(RunRow.created_at > now() - timedelta(days=1)))
    if hour >= settings.runs_per_ip_per_hour or day >= settings.runs_per_day:
        raise RateLimited("Generation limit reached, try again later. Library guides stay available.")


GENERAL_USE = "General: an AI agent that reads and writes the connected user's data"


async def start(query: str, ip: str, force: bool = False, use_case: str = "") -> dict:
    """Return an existing guide slug, join an active run, or start a new run."""
    key = query.lower().strip()
    if not force and (slug := await guides.match(query)):
        return {"slug": slug}
    if key in _active:
        return {"run_id": _active[key]}
    await _check_limits(ip)
    run_id = str(uuid.uuid4())
    async with Session() as db, db.begin():
        db.add(RunRow(id=run_id, query=query, client_ip=ip))
    _events[run_id], _waiters[run_id], _active[key] = [], asyncio.Event(), run_id
    _tasks[run_id] = asyncio.create_task(_execute(run_id, query, key, use_case or GENERAL_USE))
    return {"run_id": run_id}


async def ask(message: str, ip: str, slug: str = "") -> dict:
    """Route a chat message: app name -> guide, described need -> recommendations, question -> follow-up answer."""
    current = (await guides.get(slug)).app if slug and await guides.get(slug) else ""
    intake = await classify(message, current)
    if intake.kind in ("other", "followup", "clarify"):
        return {"kind": intake.kind, "reply": intake.reply}
    candidates = [{**c.model_dump(), "slug": await guides.match(c.name)} for c in intake.candidates]
    app = intake.app if intake.kind == "app" else candidates[0]["name"]
    try:
        started = await start(app, ip, force=intake.fresh, use_case=intake.use_case)
    except RateLimited as e:
        started = {"error": str(e)}
    return {"kind": intake.kind, "reply": intake.reply, "app": app, "use_case": intake.use_case, "candidates": candidates, **started}


async def _execute(run_id: str, query: str, key: str, use_case: str) -> None:
    status, slug, error, models, t0 = "failed", None, None, set(), time.monotonic()
    try:
        session = await sessions.create_session(app_name=APP, user_id="web", state={"query": query, "use_case": use_case})
        message = types.Content(role="user", parts=[types.Part(text=f"Investigate: {query}")])
        started, steps, blocks = set(), {}, {}  # steps: call id -> tool; blocks: agent -> open text block id
        draft, announced, last_draft = "", [], 0.0
        async for event in runner.run_async(user_id="web", session_id=session.id, new_message=message, run_config=STREAMING):
            agent = event.author
            if agent in STAGES and agent not in started:
                started.add(agent)
                _emit(run_id, "stage", id=agent, label=STAGES[agent], lane=LANES[agent], status="started")
            if agent in NARRATORS:
                # partial events carry text deltas; the complete event repeats them, so only use it if nothing streamed
                if event.partial or agent not in blocks:
                    for text in _texts(event):
                        block = blocks.setdefault(agent, f"{agent}-{len(_events[run_id])}")
                        _emit(run_id, "text", id=block, stage=agent, delta=text)
                if event.partial:
                    continue
                if agent in blocks:
                    _emit(run_id, "text_end", id=blocks.pop(agent), stage=agent, final=event.is_final_response())
            elif event.partial:
                if agent == "writer":
                    draft += "".join(_texts(event))
                    if time.monotonic() - last_draft > 1.0:  # the guide renders live in the canvas as it is written
                        last_draft = time.monotonic()
                        _emit(run_id, "draft", html=templates.get_template("_guide.html").render(g=guides.partial_guide(draft)))
                    for key, label in SECTIONS.items():
                        if key not in announced and f'"{key}"' in draft:
                            announced.append(key)
                            _emit(run_id, "step", id=f"w-{key}", stage=agent, kind="write", text=label, url="", status="started")
                continue
            if event.model_version:
                models.add(event.model_version)
            for call in event.get_function_calls():
                kind, text, url = _describe_call(call.name, call.args or {})
                steps[call.id] = call.name
                _emit(run_id, "step", id=call.id, stage=agent, kind=kind, text=text, url=url, status="started")
            for resp in event.get_function_responses():
                _emit(run_id, "step", id=resp.id, stage=agent, status="done", **_describe_result(steps.get(resp.id, ""), resp.response or {}))
            if agent in STAGES and event.is_final_response():
                for key in announced:
                    _emit(run_id, "step", id=f"w-{key}", stage=agent, status="done", result="")
                announced.clear()
                _emit(run_id, "stage", id=agent, status="done")
        state = (await sessions.get_session(app_name=APP, user_id="web", session_id=session.id)).state
        if not isinstance(state.get("guide_draft"), dict):  # the resolver found no third-party OAuth; pipeline stopped early
            raise NotIdentified("No third-party OAuth found for this app. What the agent found:\n" + state.get("app_profile", ""))
        _emit(run_id, "stage", id="validator", label="Checking evidence", status="started")
        guide = finalize(GuideDraft.model_validate(state["guide_draft"]), state, sorted(models))
        await guides.save(guide, query)
        _emit(run_id, "stage", id="validator", status="done")
        status, slug = "done", guide.slug
        usage = summarize(state)
        log.info("run %s usage: %s", run_id, usage)
        _emit(run_id, "done", slug=slug, title=guide.app, difficulty=guide.difficulty, headline=guide.headline,
              approval_wait=guide.approval_wait, seconds=round(time.monotonic() - t0), usage=usage)
    except asyncio.CancelledError:
        error = "stopped by user"
        _emit(run_id, "error", message="Research stopped. Ask again any time.", finding=True, stopped=True)
    except NotIdentified as e:  # a finding, not a failure: shown as a normal reply
        error = str(e)
        _emit(run_id, "error", message=error, finding=True)
    except Exception as e:
        log.exception("run %s failed", run_id)
        error = f"{type(e).__name__}: {str(e)[:300]}"
        _emit(run_id, "error", message="Generation failed. Please try again in a minute.")
    finally:
        _active.pop(key, None)
        _tasks.pop(run_id, None)
        async with Session() as db, db.begin():
            row = await db.get(RunRow, run_id)
            stored = [e for e in _events[run_id] if e["event"] != "draft"]  # drafts are only useful live
            row.status, row.guide_slug, row.error, row.events, row.finished_at = status, slug, error, stored, now()


async def stream(run_id: str, after: int = -1):
    """Yield events after `after`: replays stored events, then follows a live run until it ends."""
    if run_id not in _events:
        async with Session() as db:
            row = await db.get(RunRow, run_id)
        events = row.events if row and row.status != "running" else [
            {"seq": 0, "event": "error", "data": {"message": "This run was interrupted. Please ask again."}}]
        for event in events:
            if event["seq"] > after:  # by seq, not position: stored history has the drafts removed
                yield event
        return
    sent = after + 1
    while True:
        events = _events[run_id]
        for event in events[sent:]:
            yield event
            if event["event"] in ("done", "error"):
                return
        sent = len(events)
        _waiters[run_id].clear()
        try:
            await asyncio.wait_for(_waiters[run_id].wait(), timeout=15)
        except asyncio.TimeoutError:
            yield {"seq": -1, "event": "ping", "data": {}}


async def fail_interrupted() -> None:
    """Runs still marked running at startup died with the previous process."""
    async with Session() as db, db.begin():
        for row in await db.scalars(select(RunRow).where(RunRow.status == "running")):
            row.status, row.error, row.finished_at = "failed", "interrupted by restart", now()


def cancel(run_id: str) -> bool:
    task = _tasks.get(run_id)
    return bool(task and task.cancel())
