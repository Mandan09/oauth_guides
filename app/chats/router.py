import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, select

from app.chats import service
from app.chats.models import ChatRow
from app.chats.schemas import AnswerIn, ChatIn
from app.database import Session
from app.guides.models import now

router = APIRouter(prefix="/api/chats", tags=["chats"])
log = logging.getLogger(__name__)
SSE_HEADERS = {"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"}


@router.get("")
async def list_chats(client_id: str):
    async with Session() as db:
        rows = await db.scalars(select(ChatRow).where(ChatRow.client_id == client_id).order_by(ChatRow.updated_at.desc()).limit(50))
        return [{"id": r.id, "title": r.title, "updated_at": r.updated_at} for r in rows]


@router.get("/{chat_id}")
async def get_chat(chat_id: str, client_id: str):
    async with Session() as db:
        row = await db.get(ChatRow, chat_id)
    if not row or row.client_id != client_id:
        raise HTTPException(404, "Chat not found")
    return {"id": row.id, "title": row.title, "items": row.items}


@router.put("/{chat_id}")
async def save_chat(chat_id: str, body: ChatIn):
    async with Session() as db, db.begin():
        row = await db.get(ChatRow, chat_id)
        if row and row.client_id != body.client_id:
            raise HTTPException(404, "Chat not found")
        if not row:
            row = ChatRow(id=chat_id, client_id=body.client_id)
            db.add(row)
        row.title, row.items, row.updated_at = body.title, body.items, now()
    return {"ok": True}


@router.delete("/{chat_id}")
async def delete_chat(chat_id: str, client_id: str):
    async with Session() as db, db.begin():
        await db.execute(delete(ChatRow).where(ChatRow.id == chat_id, ChatRow.client_id == client_id))
    return {"ok": True}


async def _append(chat_id: str, client_id: str, item: dict) -> None:
    async with Session() as db, db.begin():
        row = await db.get(ChatRow, chat_id)
        if row and row.client_id == client_id and item not in row.items:
            row.items, row.updated_at = [*row.items, item], now()


@router.post("/{chat_id}/answer")
async def answer(chat_id: str, body: AnswerIn):
    """Stream a follow-up answer: token, step, done or error events."""
    async def sse():
        text = ""
        try:
            async for event, data in service.answer(chat_id, body.client_id, body.message, body.slug):
                text += data.get("delta", "") if event == "token" else ""
                if event == "done":  # saved server-side so the answer survives the user switching chats
                    await _append(chat_id, body.client_id, {"type": "answer", "text": text, "usage": data["usage"], "at": now().isoformat()})
                yield f"event: {event}\ndata: {json.dumps(data)}\n\n"
        except Exception:
            log.exception("answer failed for chat %s", chat_id)
            yield f"event: error\ndata: {json.dumps({'message': 'Could not answer right now. Please try again.'})}\n\n"

    return StreamingResponse(sse(), media_type="text/event-stream", headers=SSE_HEADERS)
