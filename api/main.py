"""
WheelSaver API — FastAPI REST API para consultar la BD de repos.

Uso:
    python cli.py api
    # o
    uvicorn api.main:app --reload

Documentacion automatica: http://localhost:8000/docs
"""

from fastapi import FastAPI, Query, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import aiosqlite

from api.database import get_db
from api.repository import (
    search_repos_async,
    search_repos_multi_keywords_async,
    get_stats_async,
    get_repo_async,
    get_languages_async,
    list_repos_async,
    get_top_async,
)

app = FastAPI(
    title="WheelSaver API",
    description="Busca y analiza repositorios de GitHub desde la base de datos local de WheelSaver. RAG multi-proveedor con failover automático.",
    version="3.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return RedirectResponse(url="/web/index.html")


@app.get("/health")
async def health(db: aiosqlite.Connection = Depends(get_db)):
    """Healthcheck simple."""
    stats = await get_stats_async(db)
    return {"status": "ok", "version": "3.0.0", "repos": stats["total_repos"]}


@app.get("/search")
async def search(
    q: str = Query(..., description="Keyword(s) para buscar"),
    limit: int = Query(10, ge=1, le=100, description="Max resultados"),
    language: str = Query(None, description="Filtrar por lenguaje"),
    min_stars: int = Query(0, ge=0, description="Estrellas minimas"),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Busqueda full-text en la base de datos (FTS5 + fallback LIKE)."""
    keywords = [kw.strip() for kw in q.split() if kw.strip()]
    if not keywords:
        return {"query": q, "repos": [], "total": 0}

    if len(keywords) == 1:
        repos = await search_repos_async(db, keywords[0], limit=limit)
    else:
        repos = await search_repos_multi_keywords_async(db, keywords, limit=limit)

    # Filtros post-query
    if language:
        repos = [r for r in repos if r["language"].lower() == language.lower()]
    if min_stars:
        repos = [r for r in repos if r["stars"] >= min_stars]

    return {"query": q, "repos": repos[:limit], "total": len(repos[:limit])}


@app.get("/stats")
async def api_stats(db: aiosqlite.Connection = Depends(get_db)):
    """Estadisticas de la base de datos."""
    return await get_stats_async(db)


@app.get("/repos/{owner}/{name}")
async def get_repo(owner: str, name: str, db: aiosqlite.Connection = Depends(get_db)):
    """Obtener un repositorio por owner y nombre."""
    repo = await get_repo_async(db, owner, name)
    if not repo:
        raise HTTPException(status_code=404, detail="Repositorio no encontrado")
    return repo


@app.get("/languages")
async def languages(
    limit: int = Query(50, ge=1, le=200, description="Max lenguajes"),
    min_repos: int = Query(1, ge=1, description="Min repos por lenguaje"),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Lista de lenguajes de programacion con cantidad de repos."""
    langs = await get_languages_async(db, min_repos=min_repos, limit=limit)
    return {"languages": langs}


@app.get("/repos")
async def list_repos(
    page: int = Query(1, ge=1, description="Numero de pagina"),
    per_page: int = Query(50, ge=1, le=200, description="Repos por pagina"),
    language: str = Query(None, description="Filtrar por lenguaje"),
    sort: str = Query("stars", description="Ordenar por: stars, name, updated_at"),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Lista paginada de repositorios."""
    order_col = (
        "stars" if sort == "stars" else (sort if sort in ("name", "updated_at") else "stars")
    )
    offset = (page - 1) * per_page
    repos = await list_repos_async(
        db, order_col=order_col, language=language, per_page=per_page, offset=offset
    )
    return {"page": page, "per_page": per_page, "repos": repos, "total": len(repos)}


@app.get("/top")
async def top(
    limit: int = Query(10, ge=1, le=100, description="Cuantos top repos"),
    language: str = Query(None, description="Filtrar por lenguaje"),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Top repositorios por estrellas."""
    repos = await get_top_async(db, limit=limit, language=language)
    return {"limit": limit, "repos": repos}


@app.post("/scrape")
async def trigger_scrape(
    background_tasks: BackgroundTasks,
    min_stars: int = Query(500, ge=10, description="Estrellas minimas para buscar"),
):
    """Lanza el scraper de GitHub de forma asíncrona en el mismo proceso."""
    from scraper.github_fetcher import fetch_top_repos
    background_tasks.add_task(fetch_top_repos, min_stars)
    return {"status": "ok", "message": f"Scraper iniciado (min_stars={min_stars})"}


from pydantic import BaseModel
class AskRequest(BaseModel):
    question: str

@app.post("/ask")
async def ask_agent(
    req: AskRequest,
    db: aiosqlite.Connection = Depends(get_db)
):
    """Realiza una consulta al LLM multi-proveedor (RAG) usando repositorios como contexto. Failover automático entre free tiers."""
    from api.llm import ask_llm_about_repos

    # Extraer posibles keywords de la pregunta para buscar contexto
    keywords = [kw.strip() for kw in req.question.replace("?", "").replace("¿", "").split() if len(kw) > 3]

    if len(keywords) == 1:
        repos = await search_repos_async(db, keywords[0], limit=10)
    else:
        repos = await search_repos_multi_keywords_async(db, keywords, limit=10)

    answer = await ask_llm_about_repos(req.question, repos)
    return {"question": req.question, "context_repos_used": len(repos), "answer": answer}

app.mount("/web", StaticFiles(directory="frontend", html=True), name="frontend")


