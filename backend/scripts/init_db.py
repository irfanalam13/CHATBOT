"""Create all tables directly (quick start / local dev).

For production use Alembic:
    alembic revision --autogenerate -m "init"
    alembic upgrade head
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow running directly (`python scripts/init_db.py`) by putting the backend
# root on sys.path so the `app` package is importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import Base, engine
import app.models  # noqa: F401


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("All tables created.")


if __name__ == "__main__":
    asyncio.run(main())
