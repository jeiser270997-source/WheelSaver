"""api/live_fallback.py — Fallback en vivo a la API REST de GitHub (versión async).

Extraído de api/repository.py: cuando la BD local no tiene resultados,
consulta /search/repositories y persiste los hallazgos en la BD local.
"""

import logging
import os

import aiosqlite
import httpx


async def fetch_live_github_async(db: aiosqlite.Connection, query: str, limit: int = 20) -> list[dict]:
    """Consulta la API REST de GitHub cuando la BD local no tiene resultados. Persiste en BD local."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": min(limit, 100),
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://api.github.com/search/repositories",
                headers=headers,
                params=params,
            )

        if resp.status_code == 403:
            logging.warning("GitHub API rate limit alcanzado (async live fallback)")
            return []
        if resp.status_code != 200:
            logging.warning("GitHub API respondio %s en async live fallback", resp.status_code)
            return []

        items = resp.json().get("items", [])
        logging.info("GitHub API async live: %d resultados para '%s'", len(items), query)

        live_repos = [
            {
                "name": item["name"],
                "owner": item["owner"]["login"],
                "description": item.get("description") or "",
                "url": item["html_url"],
                "stars": item["stargazers_count"],
                "language": item.get("language") or "",
                "topics": ",".join(item.get("topics", [])),
            }
            for item in items
        ]

        # Persistir en BD local
        if live_repos:
            await _upsert_repos_async(
                db,
                [
                    {
                        "id": str(item["id"]),
                        "name": item["name"],
                        "owner": item["owner"]["login"],
                        "description": item.get("description") or "",
                        "url": item["html_url"],
                        "stars": item["stargazers_count"],
                        "language": item.get("language") or "",
                        "topics": ",".join(item.get("topics", [])),
                        "updated_at": item.get("updated_at", ""),
                    }
                    for item in items
                ],
            )

        return live_repos

    except httpx.TimeoutException:
        logging.warning("Timeout en async live fallback a GitHub API")
        return []
    except Exception as e:
        logging.error("Error en async live fallback a GitHub API: %s", e)
        return []


async def _upsert_repos_async(db: aiosqlite.Connection, repos_list: list[dict]):
    """Versión asíncrona de upsert_repos para no bloquear el Event Loop."""
    data = []
    for repo in repos_list:
        data.append(
            (
                repo["id"],
                repo["name"],
                repo["owner"],
                repo.get("description", ""),
                repo["url"],
                repo["stars"],
                repo.get("language", ""),
                repo.get("topics", ""),
                repo.get("updated_at", ""),
            )
        )

    await db.executemany(
        """
        INSERT INTO repos (id, name, owner, description, url, stars, language, topics, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            owner=excluded.owner,
            description=excluded.description,
            url=excluded.url,
            stars=excluded.stars,
            language=excluded.language,
            topics=excluded.topics,
            updated_at=excluded.updated_at
        """,
        data,
    )
    await db.commit()

    # Sync FTS5 — triggers AFTER INSERT manejan sync incremental
    # No hacer rebuild manual: triggers ya actualizan repos_fts
