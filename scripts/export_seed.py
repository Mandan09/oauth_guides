"""Write every guide in the database to seed/<slug>.json, so a fresh deployment starts with the library.

Run against the local stack:
    docker compose run --rm -v ./seed:/srv/seed -v ./scripts:/srv/scripts app python -m scripts.export_seed
"""

import asyncio
import json

from sqlalchemy import select

from app.database import Session
from app.guides.models import GuideRow
from app.guides.service import SEED_DIR


async def main() -> None:
    SEED_DIR.mkdir(exist_ok=True)
    async with Session() as db:
        rows = (await db.scalars(select(GuideRow).order_by(GuideRow.slug))).all()
    for row in rows:
        (SEED_DIR / f"{row.slug}.json").write_text(json.dumps({**row.data, "origin": "seed"}, indent=2))
    print(f"exported {len(rows)} guides to {SEED_DIR}")


asyncio.run(main())
