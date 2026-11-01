from google.genai import types

from app.guide_agent.advisor import make_runner
from app.guide_agent.usage import summarize
from app.guides import service as guides
from app.runs.service import STREAMING, _describe_call, _describe_result, _texts, sessions
from app.web.templating import templates

runner = make_runner(sessions)
APP = "oauth_advisor"


async def answer(chat_id: str, client_id: str, message: str, slug: str = ""):
    """Stream an advisor answer as (event, data) pairs: token deltas, tool steps, then done."""
    guide = await guides.get(slug) if slug else None
    state = {"guide_md": templates.get_template("guide.md").render(g=guide, url="") if guide else ""}
    if not await sessions.get_session(app_name=APP, user_id=client_id, session_id=chat_id):
        await sessions.create_session(app_name=APP, user_id=client_id, session_id=chat_id, state=state)
    content = types.Content(role="user", parts=[types.Part(text=message)])
    streamed, steps = False, {}
    async for event in runner.run_async(user_id=client_id, session_id=chat_id, new_message=content,
                                        state_delta=state, run_config=STREAMING):
        if event.partial or not streamed:
            for text in _texts(event):
                yield "token", {"delta": text}
                streamed = streamed or bool(event.partial)
        if event.partial:
            continue
        streamed = False  # a complete event closes this model turn
        for call in event.get_function_calls():
            kind, text, url = _describe_call(call.name, call.args or {})
            steps[call.id] = call.name
            yield "step", {"id": call.id, "kind": kind, "text": text, "url": url, "status": "started"}
        for resp in event.get_function_responses():
            yield "step", {"id": resp.id, "status": "done", **_describe_result(steps.get(resp.id, ""), resp.response or {})}
    session = await sessions.get_session(app_name=APP, user_id=client_id, session_id=chat_id)
    yield "done", {"usage": summarize(session.state)}
