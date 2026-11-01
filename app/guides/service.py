import json
from difflib import SequenceMatcher
from pathlib import Path
from typing import get_args, get_origin

from pydantic import BaseModel
from pydantic_core import PydanticUndefined, from_json

from sqlalchemy import select

from app.database import Session
from app.guide_agent.validator import norm_url, slugify
from app.guides.models import GuideRow, GuideVersionRow, now
from app.guides.schemas import Guide

SEED_DIR = Path(__file__).resolve().parents[2] / "seed"
MATCH_THRESHOLD = 0.85


def _score(query: str, row: GuideRow) -> float:
    q = query.lower().strip()
    names = [row.name.lower(), row.slug, *[a.lower() for a in row.aliases]]
    if any(q == n or norm_url(q).split("/")[0] == n for n in names):
        return 1.0
    if row.name.lower() in q.split():  # "jira guide", "slack oauth" -> the library guide
        return 0.9
    return max(SequenceMatcher(None, q, n).ratio() + (0.2 if q in n or n in q else 0) for n in names)


async def list_guides(query: str = "") -> list[GuideRow]:
    async with Session() as db:
        rows = list((await db.scalars(select(GuideRow).order_by(GuideRow.name))).all())
    if not query:
        return rows
    scored = sorted(((_score(query, r), r) for r in rows), key=lambda x: -x[0])
    return [r for s, r in scored if s >= 0.5]


async def match(query: str) -> str | None:
    """Return the slug of a library guide that clearly matches the query."""
    async with Session() as db:
        rows = (await db.scalars(select(GuideRow))).all()
    best = max(rows, key=lambda r: _score(query, r), default=None)
    return best.slug if best and _score(query, best) >= MATCH_THRESHOLD else None


async def get(slug: str) -> Guide | None:
    async with Session() as db:
        row = await db.get(GuideRow, slug)
    return Guide.model_validate(row.data) if row else None


async def save(guide: Guide, query: str = "") -> None:
    aliases = sorted({a for a in (query.lower().strip(), norm_url(guide.website).split("/")[0], slugify(guide.provider)) if a})
    async with Session() as db, db.begin():
        row = await db.get(GuideRow, guide.slug)
        if row:
            row.version += 1
            row.aliases = sorted(set(row.aliases) | set(aliases))
            row.data, row.name, row.difficulty, row.updated_at = guide.model_dump(), guide.app, guide.difficulty, now()
        else:
            row = GuideRow(slug=guide.slug, name=guide.app, aliases=aliases, difficulty=guide.difficulty,
                           data=guide.model_dump(), version=1)
            db.add(row)
        db.add(GuideVersionRow(slug=guide.slug, version=row.version, data=guide.model_dump()))


async def load_seed() -> None:
    for path in sorted(SEED_DIR.glob("*.json")):
        guide = Guide.model_validate(json.loads(path.read_text()))
        if not await get(guide.slug):
            await save(guide)


def _lenient(model: type[BaseModel], data) -> BaseModel:
    """Build a model from incomplete data without validation; missing fields get empty defaults."""
    data = data if isinstance(data, dict) else {}
    values = {}
    for name, field in model.model_fields.items():
        value, ann = data.get(name), field.annotation
        inner = (get_args(ann) or (None,))[0] if get_origin(ann) is list else None
        if isinstance(ann, type) and issubclass(ann, BaseModel):
            values[name] = _lenient(ann, value)
        elif inner is not None:
            items = value if isinstance(value, list) else []
            is_model = isinstance(inner, type) and issubclass(inner, BaseModel)
            values[name] = [_lenient(inner, i) for i in items] if is_model else [i for i in items if isinstance(i, str)]
        elif value is None:
            values[name] = "" if field.default is PydanticUndefined else field.default
        else:
            values[name] = value
    return model.model_construct(**values)


def partial_guide(json_text: str) -> Guide:
    """The writer's JSON so far, as a Guide the page template can render (strings may be half-written)."""
    try:
        data = from_json(json_text, allow_partial="trailing-strings")
    except ValueError:
        data = {}
    return _lenient(Guide, data)
