"""
Tests for api/repository.py — async repository access layer.

Uses _run_async wrapper for async functions to avoid Python 3.14
event loop conflict between pytest-playwright and pytest-asyncio.
"""

import asyncio
import os
import sys

import aiosqlite
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from tests.conftest import SAMPLE_REPOS


def _run_async(coro, timeout=15):
    """Run coroutine in a new event loop with timeout."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(asyncio.wait_for(coro, timeout=timeout))
    finally:
        loop.close()


SCHEDULE = """CREATE TABLE repos (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, owner TEXT NOT NULL,
    description TEXT, url TEXT NOT NULL, stars INTEGER NOT NULL,
    language TEXT, topics TEXT, updated_at TEXT, is_archived INTEGER DEFAULT 0
)"""
FTS5 = """CREATE VIRTUAL TABLE repos_fts USING fts5(
    name, description, topics, content='repos', content_rowid='rowid'
)"""
IDX1 = "CREATE INDEX idx_repos_stars ON repos(stars DESC)"
IDX2 = "CREATE INDEX idx_repos_language ON repos(language)"
IDX3 = "CREATE INDEX idx_repos_owner ON repos(owner)"


async def _build_async_db():
    """Create aiosqlite in-memory DB with sample data. NOT a fixture — called per test via _run_async."""
    db = await aiosqlite.connect(":memory:")
    db.row_factory = aiosqlite.Row
    await db.execute(SCHEDULE)
    await db.execute(IDX1)
    await db.execute(IDX2)
    await db.execute(IDX3)
    await db.execute(FTS5)
    # FTS5 triggers incrementales (mismos que init_db en produccion)
    await db.executescript("""
        CREATE TRIGGER IF NOT EXISTS repos_ai AFTER INSERT ON repos BEGIN
            INSERT INTO repos_fts(rowid, name, description, topics)
            VALUES (new.rowid, new.name, new.description, new.topics);
        END;
        CREATE TRIGGER IF NOT EXISTS repos_ad AFTER DELETE ON repos BEGIN
            INSERT INTO repos_fts(repos_fts, rowid, name, description, topics)
            VALUES ('delete', old.rowid, old.name, old.description, old.topics);
        END;
        CREATE TRIGGER IF NOT EXISTS repos_au AFTER UPDATE ON repos BEGIN
            INSERT INTO repos_fts(repos_fts, rowid, name, description, topics)
            VALUES ('delete', old.rowid, old.name, old.description, old.topics);
            INSERT INTO repos_fts(rowid, name, description, topics)
            VALUES (new.rowid, new.name, new.description, new.topics);
        END;
    """)
    for repo in SAMPLE_REPOS:
        topics_str = ",".join(repo["topics"])
        await db.execute(
            "INSERT INTO repos (id, name, owner, description, url, stars, language, topics, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (repo["id"], repo["name"], repo["owner"], repo["description"], repo["url"],
             repo["stars"], repo["language"], topics_str, repo["updated_at"]),
        )
    await db.commit()
    await db.execute("INSERT INTO repos_fts(repos_fts) VALUES('rebuild')")
    await db.commit()
    return db


@pytest.fixture
def async_db():
    """Fixture: yields a fully populated aiosqlite connection."""
    db = _run_async(_build_async_db())
    yield db
    _run_async(db.close())


class TestSearchReposAsync:
    def test_search_exact(self, async_db):
        from api.repository import search_repos_async

        results = _run_async(search_repos_async(async_db, "fastapi", limit=5))
        names = [r["name"] for r in results]
        assert "fastapi" in names

    def test_search_limit(self, async_db):
        from api.repository import search_repos_async

        results = _run_async(search_repos_async(async_db, "python", limit=2))
        assert len(results) <= 2

    def test_search_no_results(self, async_db):
        from api.repository import search_repos_async

        results = _run_async(search_repos_async(async_db, "zzzznonexistent12345", limit=5))
        assert results == []

    def test_search_fallback_like(self, async_db):
        from api.repository import search_repos_async

        results = _run_async(search_repos_async(async_db, "Visual Studio", limit=5))
        names = [r["name"] for r in results]
        assert "vscode" in names


class TestSearchMultiKeywordsAsync:
    def test_multi_keyword_or(self, async_db):
        from api.repository import search_repos_multi_keywords_async

        results = _run_async(search_repos_multi_keywords_async(async_db, ["fastapi", "flask"], limit=5))
        names = [r["name"] for r in results]
        assert "fastapi" in names
        assert "flask" in names

    def test_multi_keyword_empty(self, async_db):
        from api.repository import search_repos_multi_keywords_async

        results = _run_async(search_repos_multi_keywords_async(async_db, [], limit=5))
        assert results == []

    def test_multi_keyword_special_chars(self, async_db):
        from api.repository import search_repos_multi_keywords_async

        results = _run_async(search_repos_multi_keywords_async(async_db, ['fast"api'], limit=5))
        assert isinstance(results, list)


class TestGetStatsAsync:
    def test_stats_basic(self, async_db):
        from api.repository import get_stats_async

        stats = _run_async(get_stats_async(async_db))
        assert stats["total_repos"] == 5
        assert stats["stars_max"] == 190000
        assert stats["languages"] >= 3

    def test_language_filter_handles_null(self, async_db):
        from api.repository import get_stats_async

        _run_async(async_db.execute(
            "INSERT INTO repos (id, name, owner, description, url, stars, language, topics, updated_at) "
            "VALUES ('null-lang', 'null-repo', 'null', 'desc', 'url', 10, NULL, '', '')"
        ))
        _run_async(async_db.commit())
        stats = _run_async(get_stats_async(async_db))
        assert isinstance(stats["languages"], int)


class TestGetRepoAsync:
    def test_get_existing(self, async_db):
        from api.repository import get_repo_async

        repo = _run_async(get_repo_async(async_db, "fastapi", "fastapi"))
        assert repo is not None
        assert repo["name"] == "fastapi"

    def test_get_nonexistent(self, async_db):
        from api.repository import get_repo_async

        repo = _run_async(get_repo_async(async_db, "nonexistent", "nonexistent"))
        assert repo is None


class TestGetLanguagesAsync:
    def test_languages_basic(self, async_db):
        from api.repository import get_languages_async

        langs = _run_async(get_languages_async(async_db, min_repos=1, limit=5))
        assert len(langs) >= 3
        lang_names = [l["language"] for l in langs]
        assert "Python" in lang_names

    def test_languages_min_repos(self, async_db):
        from api.repository import get_languages_async

        langs = _run_async(get_languages_async(async_db, min_repos=3, limit=5))
        assert len(langs) == 1
        assert langs[0]["language"] == "Python"


class TestListReposAsync:
    def test_list_pagination(self, async_db):
        from api.repository import list_repos_async

        page1 = _run_async(list_repos_async(async_db, "stars", "", per_page=3, offset=0))
        assert len(page1) == 3

        page2 = _run_async(list_repos_async(async_db, "stars", "", per_page=3, offset=3))
        assert len(page2) == 2

    def test_list_filter_by_language(self, async_db):
        from api.repository import list_repos_async

        repos = _run_async(list_repos_async(async_db, "stars", "Rust", per_page=10, offset=0))
        assert len(repos) == 1
        assert repos[0]["name"] == "rust"

    def test_list_order_by_stars(self, async_db):
        from api.repository import list_repos_async

        repos = _run_async(list_repos_async(async_db, "stars", "", per_page=10, offset=0))
        stars = [r["stars"] for r in repos]
        assert stars == sorted(stars, reverse=True)


class TestGetTopAsync:
    def test_top_default(self, async_db):
        from api.repository import get_top_async

        repos = _run_async(get_top_async(async_db, limit=3, language=""))
        assert len(repos) == 3
        assert repos[0]["stars"] >= repos[1]["stars"]

    def test_top_filter_by_language(self, async_db):
        from api.repository import get_top_async

        repos = _run_async(get_top_async(async_db, limit=5, language="Python"))
        assert len(repos) == 3
        for r in repos:
            assert r["language"] == "Python"
