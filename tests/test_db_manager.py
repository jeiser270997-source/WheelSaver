"""
Tests para scraper/db_manager.py

Cubre: init_db, upsert_repos, upsert_external_repos, make_repo_id,
search_repos, search_repos_multi_keywords, get_stats, rebuild_fts.

Las funciones aceptan conn= para inyectar la conexion in-memory del fixture.
"""

import sqlite3
import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_make_repo_id():
    """make_repo_id debe ser determinista y generar IDs unicos."""
    from scraper.db_manager import make_repo_id

    id1 = make_repo_id("fastapi", "fastapi")
    id2 = make_repo_id("fastapi", "fastapi")
    assert id1 == id2, "Mismo owner/name debe generar mismo ID"

    id3 = make_repo_id("FastAPI", "FastAPI")
    assert id1 == id3, "Debe ser case-insensitive"

    id4 = make_repo_id("fastapi", "flask")
    assert id1 != id4, "Distinto repo debe generar distinto ID"

    assert len(id1) == 16, "Debe tener 16 chars hex"


def test_search_repos_fts(db_with_data):
    """search_repos debe encontrar repos via FTS5."""
    from scraper.db_manager import search_repos

    results = search_repos("fastapi", conn=db_with_data)
    assert len(results) >= 1
    assert results[0]["name"] == "fastapi"


def test_search_repos_like(db_with_data):
    """search_repos debe hacer fallback a LIKE si FTS5 falla."""
    from scraper.db_manager import search_repos

    results = search_repos("fastapi", conn=db_with_data)
    assert len(results) >= 1
    assert any("fastapi" in r["name"] for r in results)


def test_search_repos_limit(db_with_data):
    """search_repos debe respetar el parametro limit."""
    from scraper.db_manager import search_repos

    results = search_repos("python", limit=2, conn=db_with_data)
    assert len(results) <= 2


def test_search_repos_empty(db_with_data):
    """search_repos sin resultados debe retornar lista vacia."""
    from scraper.db_manager import search_repos

    results = search_repos("xyznonexistent12345", conn=db_with_data)
    assert results == []


def test_search_repos_multi_keywords(db_with_data):
    """search_repos_multi_keywords con OR entre keywords."""
    from scraper.db_manager import search_repos_multi_keywords

    results = search_repos_multi_keywords(["fastapi", "flask"], conn=db_with_data)
    names = [r["name"] for r in results]
    assert "fastapi" in names
    assert "flask" in names


def test_get_stats(db_with_data):
    """get_stats debe retornar estadisticas correctas."""
    from scraper.db_manager import get_stats

    stats = get_stats(conn=db_with_data)
    assert stats["total_repos"] == 5
    assert stats["stars_min"] == 71855  # flask
    assert stats["stars_max"] == 190000  # tensorflow


def test_upsert_repos_insert(db_conn):
    """upsert_repos debe insertar un nuevo repo."""
    from scraper.db_manager import upsert_repos

    repo = {
        "id": "test123",
        "name": "new-repo",
        "owner": "test-owner",
        "description": "A new repo",
        "url": "https://github.com/test-owner/new-repo",
        "stars": 1000,
        "language": "Python",
        "topics": ["test"],
        "updated_at": "2026-01-01T00:00:00Z",
    }

    upsert_repos([repo], conn=db_conn)

    cursor = db_conn.cursor()
    cursor.execute("SELECT name, stars FROM repos WHERE id = ?", (repo["id"],))
    row = cursor.fetchone()
    assert row is not None
    assert row[0] == "new-repo"
    assert row[1] == 1000


def test_upsert_repos_update(db_conn):
    """upsert_repos debe actualizar un repo existente."""
    from scraper.db_manager import upsert_repos

    cursor = db_conn.cursor()
    cursor.execute(
        """INSERT INTO repos (id, name, owner, description, url, stars, language, topics, updated_at)
           VALUES ('update1', 'old-name', 'owner', 'desc', 'url', 500, 'Go', '', '2026-01-01')""",
    )
    db_conn.commit()

    upsert_repos(
        [
            {
                "id": "update1",
                "name": "new-name",
                "owner": "owner",
                "description": "desc",
                "url": "url",
                "stars": 999,
                "language": "Go",
                "topics": ["updated"],
                "updated_at": "2026-06-01",
            }
        ],
        conn=db_conn,
    )

    cursor.execute("SELECT name, stars FROM repos WHERE id = 'update1'")
    row = cursor.fetchone()
    assert row[0] == "new-name"
    assert row[1] == 999


def test_upsert_external_repos_generates_id(db_conn):
    """upsert_external_repos debe generar ID si no viene."""
    from scraper.db_manager import upsert_external_repos, make_repo_id

    repo = {
        "name": "auto-id-repo",
        "owner": "auto-owner",
        "description": "No id provided",
        "url": "https://github.com/auto-owner/auto-id-repo",
        "stars": 5000,
        "language": "Python",
        "topics": [],
        "updated_at": "2026-01-01T00:00:00Z",
    }

    upsert_external_repos([repo], conn=db_conn)

    expected_id = make_repo_id("auto-owner", "auto-id-repo")
    cursor = db_conn.cursor()
    cursor.execute("SELECT name, id FROM repos WHERE id = ?", (expected_id,))
    row = cursor.fetchone()
    assert row is not None
    assert row[0] == "auto-id-repo"
