import aiosqlite
from async_lru import alru_cache
import typesense
import os
import logging

TYPESENSE_API_KEY = os.getenv("TYPESENSE_API_KEY", "wheelsaver_typesense_key")
TYPESENSE_HOST = os.getenv("TYPESENSE_HOST", "localhost")

ts_client = typesense.Client({
  'nodes': [{
    'host': TYPESENSE_HOST,
    'port': '8108',
    'protocol': 'http'
  }],
  'api_key': TYPESENSE_API_KEY,
  'connection_timeout_seconds': 2
})


async def search_repos_async(db: aiosqlite.Connection, keyword: str, limit: int = 5):
    """Búsqueda vectorial/full-text mediante Typesense."""
    try:
        search_parameters = {
            'q': keyword,
            'query_by': 'name,description,topics,owner',
            'per_page': limit
        }
        res = ts_client.collections['repos'].documents.search(search_parameters)
        return [hit['document'] for hit in res['hits']]
    except Exception as e:
        logging.error(f"Error Typesense: {e}")
        return []


async def search_repos_multi_keywords_async(
    db: aiosqlite.Connection, keywords: list[str], limit: int = 5
):
    """Búsqueda con múltiples keywords en Typesense."""
    q = " ".join(keywords)
    try:
        search_parameters = {
            'q': q,
            'query_by': 'name,description,topics',
            'per_page': limit
        }
        res = ts_client.collections['repos'].documents.search(search_parameters)
        return [hit['document'] for hit in res['hits']]
    except Exception as e:
        logging.error(f"Error Typesense: {e}")
        return []


@alru_cache(maxsize=32)
async def get_stats_async(db: aiosqlite.Connection):
    stats = {}
    cursor = await db.execute("SELECT COUNT(*) as count FROM repos")
    row = await cursor.fetchone()
    stats["total_repos"] = row["count"]

    cursor = await db.execute(
        "SELECT MIN(stars) as min_s, MAX(stars) as max_s, AVG(stars) as avg_s FROM repos"
    )
    row = await cursor.fetchone()
    stats["stars_min"] = row["min_s"]
    stats["stars_max"] = row["max_s"]
    stats["stars_avg"] = round(row["avg_s"]) if row["avg_s"] else 0

    cursor = await db.execute(
        'SELECT COUNT(DISTINCT language) as cnt FROM repos WHERE language != ""'
    )
    row = await cursor.fetchone()
    stats["languages"] = row["cnt"]

    cursor = await db.execute("""
        SELECT language, COUNT(*) as cnt FROM repos
        WHERE language != "" GROUP BY language ORDER BY cnt DESC LIMIT 10
    """)
    top_langs = await cursor.fetchall()
    stats["top_languages"] = {r["language"]: r["cnt"] for r in top_langs}

    return stats


async def get_repo_async(db: aiosqlite.Connection, owner: str, name: str):
    cursor = await db.execute(
        "SELECT * FROM repos WHERE owner = ? AND name = ?",
        (owner, name),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


@alru_cache(maxsize=32)
async def get_languages_async(db: aiosqlite.Connection, min_repos: int, limit: int):
    cursor = await db.execute(
        """SELECT language, COUNT(*) as count FROM repos
           WHERE language != '' GROUP BY language
           HAVING count >= ? ORDER BY count DESC LIMIT ?""",
        (min_repos, limit),
    )
    langs = await cursor.fetchall()
    return [{"language": r["language"], "repos": r["count"]} for r in langs]


async def list_repos_async(
    db: aiosqlite.Connection, order_col: str, language: str, per_page: int, offset: int
):
    if language:
        cursor = await db.execute(
            f"SELECT * FROM repos WHERE language = ? ORDER BY {order_col} DESC LIMIT ? OFFSET ?",
            (language, per_page, offset),
        )
    else:
        cursor = await db.execute(
            f"SELECT * FROM repos ORDER BY {order_col} DESC LIMIT ? OFFSET ?",
            (per_page, offset),
        )
    repos = await cursor.fetchall()
    return [dict(r) for r in repos]


async def get_top_async(db: aiosqlite.Connection, limit: int, language: str):
    if language:
        cursor = await db.execute(
            "SELECT * FROM repos WHERE language = ? ORDER BY stars DESC LIMIT ?",
            (language, limit),
        )
    else:
        cursor = await db.execute(
            "SELECT * FROM repos ORDER BY stars DESC LIMIT ?",
            (limit,),
        )
    repos = await cursor.fetchall()
    return [dict(r) for r in repos]
