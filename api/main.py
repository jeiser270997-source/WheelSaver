"""
WheelSaver API — FastAPI REST API para consultar la BD de repos.

Uso:
    python cli.py api
    # o
    uvicorn api.main:app --reload

Documentacion automatica: http://localhost:8000/docs
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from scraper.db_manager import (
    search_repos,
    search_repos_multi_keywords,
    get_stats,
    DB_PATH,
)

import sqlite3

app = FastAPI(
    title="WheelSaver API",
    description="Busca y analiza repositorios de GitHub desde la base de datos local de WheelSaver",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Healthcheck simple."""
    return {"status": "ok", "version": "3.0.0", "repos": get_stats()["total_repos"]}


@app.get("/search")
def search(
    q: str = Query(..., description="Keyword(s) para buscar"),
    limit: int = Query(10, ge=1, le=100, description="Max resultados"),
    language: str = Query(None, description="Filtrar por lenguaje"),
    min_stars: int = Query(0, ge=0, description="Estrellas minimas"),
):
    """Busqueda full-text en la base de datos (FTS5 + fallback LIKE)."""
    keywords = [kw.strip() for kw in q.split() if kw.strip()]
    if not keywords:
        return {"query": q, "repos": [], "total": 0}

    if len(keywords) == 1:
        repos = search_repos(keywords[0], limit=limit)
    else:
        repos = search_repos_multi_keywords(keywords, limit=limit)

    # Filtros post-query
    if language:
        repos = [r for r in repos if r["language"].lower() == language.lower()]
    if min_stars:
        repos = [r for r in repos if r["stars"] >= min_stars]

    return {"query": q, "repos": repos[:limit], "total": len(repos[:limit])}


@app.get("/stats")
def api_stats():
    """Estadisticas de la base de datos."""
    return get_stats()


@app.get("/repos/{owner}/{name}")
def get_repo(owner: str, name: str):
    """Obtener un repositorio por owner y nombre."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM repos WHERE owner = ? AND name = ?",
        (owner, name),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Repositorio no encontrado")

    return dict(row)


@app.get("/languages")
def languages(
    limit: int = Query(50, ge=1, le=200, description="Max lenguajes"),
    min_repos: int = Query(1, ge=1, description="Min repos por lenguaje"),
):
    """Lista de lenguajes de programacion con cantidad de repos."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """SELECT language, COUNT(*) as count FROM repos
           WHERE language != '' GROUP BY language
           HAVING count >= ? ORDER BY count DESC LIMIT ?""",
        (min_repos, limit),
    )
    langs = [{"language": r[0], "repos": r[1]} for r in cursor.fetchall()]
    conn.close()
    return {"languages": langs}


@app.get("/repos")
def list_repos(
    page: int = Query(1, ge=1, description="Numero de pagina"),
    per_page: int = Query(50, ge=1, le=200, description="Repos por pagina"),
    language: str = Query(None, description="Filtrar por lenguaje"),
    sort: str = Query("stars", description="Ordenar por: stars, name, updated_at"),
):
    """Lista paginada de repositorios."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    order_col = "stars" if sort == "stars" else (sort if sort in ("name", "updated_at") else "stars")

    if language:
        cursor.execute(
            f"SELECT * FROM repos WHERE language = ? ORDER BY {order_col} DESC LIMIT ? OFFSET ?",
            (language, per_page, (page - 1) * per_page),
        )
    else:
        cursor.execute(
            f"SELECT * FROM repos ORDER BY {order_col} DESC LIMIT ? OFFSET ?",
            (per_page, (page - 1) * per_page),
        )

    repos = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"page": page, "per_page": per_page, "repos": repos, "total": len(repos)}


@app.get("/top")
def top(
    limit: int = Query(10, ge=1, le=100, description="Cuantos top repos"),
    language: str = Query(None, description="Filtrar por lenguaje"),
):
    """Top repositorios por estrellas."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if language:
        cursor.execute(
            "SELECT * FROM repos WHERE language = ? ORDER BY stars DESC LIMIT ?",
            (language, limit),
        )
    else:
        cursor.execute(
            "SELECT * FROM repos ORDER BY stars DESC LIMIT ?",
            (limit,),
        )

    repos = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"limit": limit, "repos": repos}
