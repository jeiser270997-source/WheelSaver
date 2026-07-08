import pytest
from httpx import AsyncClient, ASGITransport
from api.main import app


@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "repos" in data


@pytest.mark.asyncio
async def test_stats():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_repos" in data
    assert "top_languages" in data


@pytest.mark.asyncio
async def test_search():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/search?q=fastapi&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert data["query"] == "fastapi"
    assert "repos" in data
    assert len(data["repos"]) <= 2


@pytest.mark.asyncio
async def test_languages():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/languages?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "languages" in data
    assert len(data["languages"]) <= 5


@pytest.mark.asyncio
async def test_top():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/top?limit=3")
    assert response.status_code == 200
    data = response.json()
    assert "repos" in data
    assert len(data["repos"]) <= 3


@pytest.mark.asyncio
async def test_list_repos():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/repos?page=1&per_page=10")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["per_page"] == 10
    assert "repos" in data
    assert len(data["repos"]) <= 10
