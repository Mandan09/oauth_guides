import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.chats.router import router as chats_router
from app.database import init_db
from app.guides import service as guides
from app.guides.router import router as guides_router
from app.runs.router import router as runs_router
from app.runs.service import fail_interrupted
from app.web.router import router as web_router

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    await guides.load_seed()
    await fail_interrupted()
    yield


app = FastAPI(title="OAuth App Guides", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "web" / "static"), name="static")
app.include_router(guides_router)
app.include_router(runs_router)
app.include_router(chats_router)
app.include_router(web_router)


@app.get("/healthz", include_in_schema=False)
async def healthz():
    return {"ok": True}
