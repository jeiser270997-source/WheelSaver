"""
scraper/search.py — Búsqueda FTS5 + scoring determinista + live fallback.

Extraído de db_manager.py para mantener responsabilidad única:
- db_manager.py: esquema, conexión, upserts, estadísticas.
- synonyms.py: diccionario offline de sinónimos técnicos.
- search.py: búsqueda full-text, scoring multi-factor y fallback a GitHub API.
"""

import os
import re
import sqlite3

import httpx
from loguru import logger

from scraper.scoring import calculate_repo_score
from scraper.synonyms import expand_keywords_offline

# NOTA: NO importar db_manager a nivel de módulo — db_manager re-exporta desde
# aquí, lo que crearía un import circular. Se usan imports locales dentro de
# las funciones que los necesitan.


def clean_fts_term(term: str) -> str:
    """Escapa y limpia un termino individual para FTS5."""
    t = re.sub(r'[*():^"=\\]', '', str(term)).strip()
    if '-' in t or '.' in t or '+' in t:
        return f'"{t}"'
    return t


def search_repos(keyword, limit=5, conn=None):
    """Busca repos por keyword usando FTS5 y scoring determinista inteligente."""
    terms = [keyword] if isinstance(keyword, str) else keyword
    return search_repos_multi_keywords(terms, limit=limit, conn=conn)


_FTS_QUERY = """
    SELECT r.name, r.owner, r.description, r.url, r.stars, r.language, r.topics, r.updated_at, r.is_archived
    FROM repos_fts f
    JOIN repos r ON r.rowid = f.rowid
    WHERE repos_fts MATCH ?
    LIMIT ?
"""


def search_repos_multi_keywords(keywords, limit=20, conn=None):
    """
    Busca repos que matcheen CUALQUIERA de las keywords dadas usando FTS5 + scoring determinista multi-factor.
    """
    if isinstance(keywords, str):
        keywords = keywords.strip().split()

    expanded_terms = expand_keywords_offline(keywords)

    from scraper.db_manager import init_db

    owns_conn = False
    if conn is None:
        conn = init_db()
        owns_conn = True

    try:
        cursor = conn.cursor()
        rows = _query_fts_rows(cursor, keywords, expanded_terms)
        if not rows and keywords:
            rows = _query_like_rows(cursor, keywords)
    finally:
        if owns_conn:
            conn.close()

    repos = _rows_to_repos(rows, keywords)

    # Live fallback
    if not repos and owns_conn and keywords:
        repo_dicts = _fetch_live_github(" ".join(keywords), limit)
        if repo_dicts:
            logger.info("+{} repos encontrados via GitHub API y guardados en BD local", len(repo_dicts))
            repos = repo_dicts[:limit]

    return repos[:limit]


def _query_fts_rows(cursor, keywords: list[str], expanded_terms: list[str]) -> list:
    """Ejecuta FTS5 con AND estricto y OR expandido como fallback. Devuelve filas sin duplicar."""
    fts_terms = [clean_fts_term(kw) for kw in expanded_terms if kw.strip()]
    if not fts_terms:
        return []

    rows = []
    try:
        # 1. Probar AND estricto primero con las palabras originales
        orig_fts_terms = [clean_fts_term(kw) for kw in keywords if kw.strip()]
        if orig_fts_terms:
            and_fts_query = " AND ".join(orig_fts_terms)
            cursor.execute(_FTS_QUERY, (and_fts_query, 100))
            rows = cursor.fetchall()

        # 2. Si trae pocos resultados, probar OR expandido
        if len(rows) < 5:
            or_fts_query = " OR ".join(fts_terms)
            cursor.execute(_FTS_QUERY, (or_fts_query, 200))
            rows.extend(cursor.fetchall())
    except sqlite3.OperationalError:
        return []

    # Deduplicar por slug (AND + OR pueden traer el mismo repo)
    seen = set()
    deduped = []
    for r in rows:
        key = f"{r[1]}/{r[0]}".lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    return deduped


def _query_like_rows(cursor, keywords: list[str]) -> list:
    """Fallback a LIKE cuando FTS5 no retorna filas."""
    like_kw = f"%{' '.join(keywords)}%"
    cursor.execute(
        """
        SELECT name, owner, description, url, stars, language, topics, updated_at, is_archived
        FROM repos
        WHERE name LIKE ? OR description LIKE ? OR topics LIKE ?
        ORDER BY stars DESC
        LIMIT 100
        """,
        (like_kw, like_kw, like_kw),
    )
    return cursor.fetchall()


def _rows_to_repos(rows: list, query_terms: list[str]) -> list[dict]:
    """Convierte filas SQL a dicts y les calcula el score determinista."""
    repos = []
    seen = set()
    for r in rows:
        slug = f"{r[1]}/{r[0]}".lower()
        if slug in seen:
            continue
        seen.add(slug)

        repo_dict = {
            "name": r[0],
            "owner": r[1],
            "description": r[2] or "",
            "url": r[3],
            "stars": r[4],
            "language": r[5] or "",
            "topics": r[6] or "",
            "updated_at": r[7] if len(r) > 7 else "",
            "is_archived": bool(r[8]) if len(r) > 8 else False,
        }
        repo_dict["_score"] = calculate_repo_score(repo_dict, query_terms)
        repos.append(repo_dict)

    # Ordenar por score determinista descendente
    repos.sort(key=lambda x: (x.get("_score", 0), x.get("stars", 0)), reverse=True)
    return repos


def _fetch_live_github(query: str, limit: int = 20) -> list[dict]:
    """
    Consulta la API REST de GitHub (/search/repositories) cuando la BD local
    no tiene resultados. Usa GITHUB_TOKEN del entorno si existe.
    Los resultados se persisten en la BD local para futuras consultas.
    """
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
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                "https://api.github.com/search/repositories",
                headers=headers,
                params=params,
            )

        if resp.status_code == 403:
            logger.warning("GitHub API rate limit alcanzado (live fallback)")
            return []
        if resp.status_code != 200:
            logger.warning("GitHub API respondio {} en live fallback", resp.status_code)
            return []

        items = resp.json().get("items", [])
        logger.info("GitHub API live: {} resultados para '{}'", len(items), query)

        live_repos = []
        for item in items:
            repo = {
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
            live_repos.append(repo)

        # Persistir en BD local para futuras consultas
        if live_repos:
            from scraper.db_manager import upsert_repos

            upsert_repos(live_repos)

        return live_repos

    except httpx.TimeoutException:
        logger.warning("Timeout en live fallback a GitHub API")
        return []
    except Exception as e:
        logger.error("Error en live fallback a GitHub API: {}", e)
        return []
