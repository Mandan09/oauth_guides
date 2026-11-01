import json

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.config import settings
from app.runs import service
from app.runs.schemas import AskRequest, RunRequest, RunStarted

router = APIRouter(prefix="/api/runs", tags=["runs"])
# no-transform and X-Accel-Buffering stop proxies (Render, nginx) from holding the stream back
SSE_HEADERS = {"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"}


def _ip(request: Request) -> str:
    return request.headers.get("x-forwarded-for", request.client.host if request.client else "").split(",")[0]


@router.post("/ask")
async def ask(body: AskRequest, request: Request):
    """Chat entry point: understands app names and free-form needs."""
    return await service.ask(body.message, _ip(request), body.slug)


@router.post("", response_model=RunStarted)
async def start_run(body: RunRequest, request: Request, x_admin_token: str = Header("")):
    if body.force and (not settings.admin_token or x_admin_token != settings.admin_token):
        raise HTTPException(403, "Regenerating needs the admin token")
    try:
        return await service.start(body.query, _ip(request), body.force, body.use_case)
    except service.RateLimited as e:
        raise HTTPException(429, str(e))


@router.post("/{run_id}/cancel")
async def cancel_run(run_id: str):
    if not service.cancel(run_id):
        raise HTTPException(404, "No running research with that id")
    return {"ok": True}


@router.get("/{run_id}/events")
async def run_events(run_id: str, last_event_id: int = Header(-1)):
    """Named SSE events with ids, so a reconnecting browser resumes where it left off."""
    async def sse():
        async for ev in service.stream(run_id, last_event_id):
            head = f"id: {ev['seq']}\n" if ev["seq"] >= 0 else ""
            yield f"{head}event: {ev['event']}\ndata: {json.dumps(ev['data'])}\n\n"

    return StreamingResponse(sse(), media_type="text/event-stream", headers=SSE_HEADERS)
