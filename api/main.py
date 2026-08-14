"""
WheelSaver API — FastAPI REST API para consultar la BD de repos.

Uso:
    python cli.py api
    # o
    uvicorn api.main:app --reload

Documentacion automatica: http://localhost:8000/docs
"""

import asyncio
import hmac
import os
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from api.database import DB_PATH, get_db
from api.repository import (
    get_languages_async,
    get_repo_async,
    get_stats_async,
    get_top_async,
    list_repos_async,
    search_repos_async,
    search_repos_multi_keywords_async,
)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="WheelSaver API",
    description="Busca y analiza repositorios de GitHub desde la base de datos local de WheelSaver. RAG multi-proveedor con failover automático.",
    version="3.3.2",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS restringido por defecto a localhost; ampliable via ALLOWED_ORIGINS="https://a.com,https://b.com"
_DEFAULT_ORIGINS = "http://127.0.0.1:8000,http://localhost:8000"
_ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", _DEFAULT_ORIGINS).split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=False,
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
    return {"status": "ok", "version": app.version, "repos": stats["total_repos"]}


@app.get("/search")
@limiter.limit("20/minute")
async def search(
    request: Request,  # noqa: F841 — requerido por slowapi (rate limiting)
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

    # Filtros post-query (safe: language puede ser None)
    if language:
        repos = [r for r in repos if r.get("language") and r["language"].lower() == language.lower()]
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
    order_col = "stars" if sort == "stars" else (sort if sort in ("name", "updated_at") else "stars")
    offset = (page - 1) * per_page
    repos = await list_repos_async(db, order_col=order_col, language=language, per_page=per_page, offset=offset)
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
@limiter.limit("1/hour")
async def trigger_scrape(
    request: Request,  # noqa: F841 — requerido por slowapi (rate limiting)
    background_tasks: BackgroundTasks,
    min_stars: int = Query(500, ge=10, description="Estrellas minimas para buscar"),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
):
    """
    Lanza el scraper de GitHub de forma asíncrona en el mismo proceso.
    Limitado a 1 vez por hora por IP. Requiere SCRAPE_ENABLED=1 o X-API-Key válido si SCRAPE_API_KEY está configurado.
    """
    from scraper.github_fetcher import fetch_top_repos

    # Validar autorización por env var o header
    scrape_enabled = os.getenv("SCRAPE_ENABLED", "1") == "1"
    required_key = os.getenv("SCRAPE_API_KEY")

    if not scrape_enabled:
        raise HTTPException(status_code=403, detail="El endpoint /scrape está deshabilitado en esta instancia.")

    # Comparación en tiempo constante — evita timing attacks en el API key
    if required_key and (not x_api_key or not hmac.compare_digest(x_api_key.encode(), required_key.encode())):
        raise HTTPException(status_code=401, detail="Header X-API-Key inválido o ausente.")

    STALE_TIMEOUT_HOURS = 6

    try:
        db = await aiosqlite.connect(DB_PATH)
    except Exception:
        # La BD aun no existe (fresh install) — continuar sin lock
        background_tasks.add_task(asyncio.to_thread, fetch_top_repos, min_stars)
        return {"status": "ok", "message": f"Scraper iniciado (min_stars={min_stars})"}

    db.row_factory = aiosqlite.Row

    try:
        now = datetime.now(timezone.utc).isoformat()

        # Asegurar existencia de tabla run_history para evitar carreras en primer uso
        await db.execute("""
            CREATE TABLE IF NOT EXISTS run_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT,
                finished_at TEXT,
                status TEXT
            )
        """)

        # 1. Auto-recuperar locks stale (> 6h)
        cursor = await db.execute("SELECT id, started_at FROM run_history WHERE status = 'running'")
        rows = await cursor.fetchall()
        for row in rows:
            started_at = datetime.fromisoformat(row["started_at"].replace("Z", "+00:00"))
            if (datetime.now(timezone.utc) - started_at).total_seconds() / 3600 >= STALE_TIMEOUT_HOURS:
                await db.execute(
                    "UPDATE run_history SET status = 'failed', finished_at = ? WHERE id = ? AND status = 'running'",
                    (now, row["id"]),
                )

        # 2. Lock atómico: una sola sentencia combina verificación + inserción
        #    Si ya existe una fila con status='running', el INSERT no inserta nada
        cursor = await db.execute(
            """
            INSERT INTO run_history (started_at, status)
            SELECT ?, 'running'
            WHERE NOT EXISTS (SELECT 1 FROM run_history WHERE status = 'running')
            """,
            (now,),
        )

        if cursor.rowcount == 0:
            # El lock no se adquirió — alguien más ya tiene uno corriendo
            await db.close()
            raise HTTPException(
                status_code=409,
                detail=f"Ya hay un scraper en ejecucion. Espera a que termine o {STALE_TIMEOUT_HOURS}h para auto-recuperacion.",
            )

        new_run_id = cursor.lastrowid
        await db.commit()
    except aiosqlite.OperationalError:
        new_run_id = None
        await db.commit()
    finally:
        await db.close()

    # 3. Programar background task en hilo separado (no bloquea event loop)
    background_tasks.add_task(asyncio.to_thread, fetch_top_repos, min_stars, new_run_id)
    return {
        "status": "ok",
        "message": f"Scraper iniciado (run_id={new_run_id}, min_stars={min_stars})",
    }


class AskRequest(BaseModel):
    question: str


@app.post("/ask")
@limiter.limit("5/minute")
async def ask_agent(request: Request, req: AskRequest, db: aiosqlite.Connection = Depends(get_db)):  # noqa: F841 — request requerido por slowapi
    """Realiza una consulta al LLM multi-proveedor (RAG) usando repositorios como contexto. Failover automático entre free tiers."""
    from api.llm import ask_llm_about_repos, expand_search_query

    # Extraer keywords usando el LLM para busqueda inteligente
    keywords = await expand_search_query(req.question)

    if not keywords:
        repos = []
    elif len(keywords) == 1:
        repos = await search_repos_async(db, keywords[0], limit=10)
    else:
        repos = await search_repos_multi_keywords_async(db, keywords, limit=10)

    answer = await ask_llm_about_repos(req.question, repos)
    return {"question": req.question, "context_repos_used": len(repos), "answer": answer}


# Ruta resuelta contra __file__ — funciona sin importar el cwd desde donde se ejecute
_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/web", StaticFiles(directory=_FRONTEND_DIR, html=True), name="frontend")
