import aiosqlite
import pytest
from httpx import ASGITransport, AsyncClient

from api.database import get_db
from api.main import app


async def _build_empty_test_db():
    """Crea BD SQLite async in-memory VACIA (para test de healthcheck sin datos)."""
    db = await aiosqlite.connect(":memory:")
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL;")
    await db.execute("""
        CREATE TABLE repos (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            owner TEXT NOT NULL,
            description TEXT,
            url TEXT NOT NULL,
            stars INTEGER NOT NULL,
            language TEXT,
            topics TEXT,
            updated_at TEXT,
            is_archived INTEGER DEFAULT 0
        )
    """)
    await db.execute("CREATE INDEX idx_repos_stars ON repos(stars DESC)")
    await db.execute("CREATE INDEX idx_repos_language ON repos(language)")
    await db.execute("CREATE INDEX idx_repos_owner ON repos(owner)")
    await db.execute("""
        CREATE VIRTUAL TABLE repos_fts USING fts5(
            name, description, topics,
            content='repos',
            content_rowid='rowid'
        )
    """)
    await db.commit()
    return db


@pytest.mark.asyncio
async def test_health(async_test_db):
    """Healthcheck debe funcionar con BD en memoria."""
    app.dependency_overrides[get_db] = lambda: async_test_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["repos"] == 5  # 5 repos en SAMPLE_REPOS
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_stats(async_test_db):
    """Stats debe retornar datos correctos de BD en memoria."""
    app.dependency_overrides[get_db] = lambda: async_test_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_repos"] == 5
    assert "Python" in data["top_languages"]
    assert data["top_languages"]["Python"] == 3  # fastapi, flask, tensorflow
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_search(async_test_db):
    """Busqueda FTS5 debe encontrar repos en BD en memoria."""
    app.dependency_overrides[get_db] = lambda: async_test_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/search?q=fastapi&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "fastapi"
    assert len(data["repos"]) >= 1
    names = [r["name"] for r in data["repos"]]
    assert "fastapi" in names
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_search_multi_keyword(async_test_db):
    """Busqueda multi-keyword debe funcionar."""
    app.dependency_overrides[get_db] = lambda: async_test_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/search?q=fastapi+flask&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "fastapi flask"  # + se decodifica como espacio en URL
    names = [r["name"] for r in data["repos"]]
    assert "fastapi" in names
    assert "flask" in names
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_search_filter_language(async_test_db):
    """Busqueda + filtro por lenguaje debe devolver solo repos de ese lenguaje."""
    app.dependency_overrides[get_db] = lambda: async_test_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/search?q=rust&language=Rust&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data["repos"]) >= 1, "Debe encontrar al menos 1 repo en Rust"
    for r in data["repos"]:
        assert r["language"] == "Rust"
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_languages(async_test_db):
    """Endpoint de lenguajes debe listar los disponibles."""
    app.dependency_overrides[get_db] = lambda: async_test_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/languages?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data["languages"]) >= 3  # Python, Rust, TypeScript
    langs = {l["language"] for l in data["languages"]}
    assert "Python" in langs
    assert "Rust" in langs
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_top(async_test_db):
    """Top repos debe devolverlos ordenados por estrellas descendente."""
    app.dependency_overrides[get_db] = lambda: async_test_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/top?limit=3")
    assert response.status_code == 200
    data = response.json()
    assert len(data["repos"]) == 3
    stars = [r["stars"] for r in data["repos"]]
    assert stars == sorted(stars, reverse=True)
    assert data["repos"][0]["name"] == "tensorflow"  # 190k estrellas
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_top_by_language(async_test_db):
    """Top repos filtrado por lenguaje."""
    app.dependency_overrides[get_db] = lambda: async_test_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/top?limit=5&language=Python")
    assert response.status_code == 200
    data = response.json()
    assert len(data["repos"]) == 3  # 3 Python repos en sample
    for r in data["repos"]:
        assert r["language"] == "Python"
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_repos(async_test_db):
    """Listado paginado de repos debe funcionar."""
    app.dependency_overrides[get_db] = lambda: async_test_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/repos?page=1&per_page=3")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["per_page"] == 3
    assert len(data["repos"]) == 3
    assert data["repos"][0]["name"] == "tensorflow"
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_repo(async_test_db):
    """Obtener un repo especifico por owner/name."""
    app.dependency_overrides[get_db] = lambda: async_test_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/repos/fastapi/fastapi")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "fastapi"
    assert data["owner"] == "fastapi"
    assert data["stars"] == 100209
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_repo_not_found(async_test_db):
    """Repo inexistente debe devolver 404."""
    app.dependency_overrides[get_db] = lambda: async_test_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/repos/nonexistent/repo")
    assert response.status_code == 404
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_no_repos():
    """Healthcheck debe funcionar incluso con BD vacia (sin repos)."""
    empty_db = await _build_empty_test_db()
    app.dependency_overrides[get_db] = lambda: empty_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["repos"] == 0
    app.dependency_overrides.clear()
    await empty_db.close()
