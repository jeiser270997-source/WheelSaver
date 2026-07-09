import aiosqlite
from async_lru import alru_cache
import logging

async def search_repos_async(db: aiosqlite.Connection, keyword: str, limit: int = 5):
    """Busqueda vectorial/full-text en SQLite (FTS5 + fallback LIKE)."""
    try:
        cursor = await db.execute(
            """
            SELECT r.name, r.owner, r.description, r.url, r.stars, r.language, r.topics
            FROM repos_fts f
            JOIN repos r ON r.rowid = f.rowid
            WHERE repos_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (keyword, limit),
        )
        results = await cursor.fetchall()

        if not results:
            cursor = await db.execute(
                """
                SELECT name, owner, description, url, stars, language, topics
                FROM repos
                WHERE name LIKE ? OR description LIKE ?
                ORDER BY stars DESC
                LIMIT ?
                """,
                (f"%{keyword}%", f"%{keyword}%", limit),
            )
            results = await cursor.fetchall()

        return [dict(r) for r in results]
    except Exception as e:
        logging.error(f"Error búsqueda asíncrona: {e}")
        return []

async def search_repos_multi_keywords_async(
    db: aiosqlite.Connection, keywords: list[str], limit: int = 5
):
    """Busqueda con multiples keywords en FTS5 (AND) con fallback individual (OR)."""
    if not keywords:
        return []

    fts_query_and = " AND ".join(f'"{kw}"' for kw in keywords)

    try:
        cursor = await db.execute(
            """
            SELECT r.name, r.owner, r.description, r.url, r.stars, r.language, r.topics
            FROM repos_fts f
            JOIN repos r ON r.rowid = f.rowid
            WHERE repos_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (fts_query_and, limit),
        )
        results = await cursor.fetchall()

        if len(results) < limit:
            results_list = [dict(r) for r in results]
            seen = {r["name"] for r in results_list}

            fts_query_or = " OR ".join(f'"{kw}"' for kw in keywords)
            cursor = await db.execute(
                """
                SELECT r.name, r.owner, r.description, r.url, r.stars, r.language, r.topics
                FROM repos_fts f
                JOIN repos r ON r.rowid = f.rowid
                WHERE repos_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (fts_query_or, limit * 2),
            )
            fallback_results = await cursor.fetchall()

            for r in fallback_results:
                r_dict = dict(r)
                if r_dict["name"] not in seen:
                    seen.add(r_dict["name"])
                    results_list.append(r_dict)
                    if len(results_list) >= limit:
                        break
            return results_list
        return [dict(r) for r in results]
    except Exception as e:
        logging.error(f"Error búsqueda asíncrona multi-keyword: {e}")
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
