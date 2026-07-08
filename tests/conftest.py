"""conftest.py — Fixtures de prueba para WheelSaver.

Provee una base de datos SQLite in-memory con el mismo esquema
que la BD real, mas repos de muestra para los tests.
"""

import sqlite3
import os
import sys
import pytest
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scraper.db_manager import make_repo_id, DB_PATH


SAMPLE_REPOS = [
    {
        "id": make_repo_id("fastapi", "fastapi"),
        "name": "fastapi",
        "owner": "fastapi",
        "description": "FastAPI framework for building APIs",
        "url": "https://github.com/fastapi/fastapi",
        "stars": 100209,
        "language": "Python",
        "topics": ["api", "python", "web"],
        "updated_at": "2026-06-01T00:00:00Z",
    },
    {
        "id": make_repo_id("pallets", "flask"),
        "name": "flask",
        "owner": "pallets",
        "description": "The Python micro framework for building web applications",
        "url": "https://github.com/pallets/flask",
        "stars": 71855,
        "language": "Python",
        "topics": ["python", "web", "framework"],
        "updated_at": "2026-05-15T00:00:00Z",
    },
    {
        "id": make_repo_id("rust-lang", "rust"),
        "name": "rust",
        "owner": "rust-lang",
        "description": "Empowering everyone to build reliable and efficient software",
        "url": "https://github.com/rust-lang/rust",
        "stars": 102345,
        "language": "Rust",
        "topics": ["rust", "language", "compiler"],
        "updated_at": "2026-06-10T00:00:00Z",
    },
    {
        "id": make_repo_id("microsoft", "vscode"),
        "name": "vscode",
        "owner": "microsoft",
        "description": "Visual Studio Code",
        "url": "https://github.com/microsoft/vscode",
        "stars": 175000,
        "language": "TypeScript",
        "topics": ["editor", "code", "typescript"],
        "updated_at": "2026-06-12T00:00:00Z",
    },
    {
        "id": make_repo_id("tensorflow", "tensorflow"),
        "name": "tensorflow",
        "owner": "tensorflow",
        "description": "An Open Source Machine Learning Framework for Everyone",
        "url": "https://github.com/tensorflow/tensorflow",
        "stars": 190000,
        "language": "Python",
        "topics": ["machine-learning", "deep-learning", "python"],
        "updated_at": "2026-06-14T00:00:00Z",
    },
]


def build_test_db():
    """Crea una BD SQLite in-memory con esquema completo + FTS5 + datos."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    cursor.execute("""
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

    cursor.execute("CREATE INDEX idx_repos_stars ON repos(stars DESC)")
    cursor.execute("CREATE INDEX idx_repos_language ON repos(language)")
    cursor.execute("CREATE INDEX idx_repos_owner ON repos(owner)")

    cursor.execute("""
        CREATE VIRTUAL TABLE repos_fts USING fts5(
            name, description, topics,
            content='repos',
            content_rowid='rowid'
        )
    """)

    conn.commit()
    return conn


@pytest.fixture
def db_conn():
    """Fixture: conexion a BD in-memory con esquema completo."""
    conn = build_test_db()
    yield conn
    conn.close()


@pytest.fixture
def db_with_data(db_conn):
    """Fixture: BD in-memory con esquema + repos de muestra insertados."""
    cursor = db_conn.cursor()
    for repo in SAMPLE_REPOS:
        topics_str = ",".join(repo["topics"])
        cursor.execute(
            """INSERT INTO repos (id, name, owner, description, url, stars, language, topics, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                repo["id"],
                repo["name"],
                repo["owner"],
                repo["description"],
                repo["url"],
                repo["stars"],
                repo["language"],
                topics_str,
                repo["updated_at"],
            ),
        )
    db_conn.commit()
    # Reconstruir indice FTS5
    cursor.execute("INSERT INTO repos_fts(repos_fts) VALUES('rebuild')")
    db_conn.commit()
    return db_conn
