import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "top_repos.db")


async def get_db():
    """Dependencia de FastAPI para obtener una sesión asíncrona de BD."""
    db = await aiosqlite.connect(DB_PATH)
    await db.execute("PRAGMA journal_mode=WAL;")
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()
