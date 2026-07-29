import os
import shutil

import aiosqlite

from scraper.db_manager import get_db_path

DB_PATH = get_db_path()


async def get_db():
    """Dependencia de FastAPI para obtener una sesión asíncrona de BD."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    if not os.path.exists(DB_PATH):
        seed_db = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "top_repos.db")
        if os.path.exists(seed_db):
            shutil.copy2(seed_db, DB_PATH)

    db = await aiosqlite.connect(DB_PATH)
    await db.execute("PRAGMA journal_mode=WAL;")
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()
