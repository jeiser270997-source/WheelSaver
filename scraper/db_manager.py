"""
scraper/db_manager.py — ORM ligero y gestión de la BD SQLite de WheelSaver.

Responsabilidad única: esquema, conexión, upserts, estadísticas e índice FTS5.
La búsqueda (FTS5 + scoring + live fallback) vive en scraper/search.py.
"""

import hashlib
import os
import re
import shutil
import sqlite3

from loguru import logger

# Re-export de búsqueda y scoring para backward-compatibilidad de imports:
#   from scraper.db_manager import search_repos, calculate_repo_score, ...
# El patrón `as X` + noqa evita que ruff elimine los re-exports (F401).
from scraper.scoring import calculate_repo_score as calculate_repo_score  # noqa: F401
from scraper.search import clean_fts_term as clean_fts_term  # noqa: F401
from scraper.search import expand_keywords_offline as expand_keywords_offline  # noqa: F401
from scraper.search import search_repos as search_repos  # noqa: F401
from scraper.search import (
    search_repos_multi_keywords as search_repos_multi_keywords,
)


def get_db_path() -> str:
    # 1. Variable de entorno
    if "WHEELSAVER_DB_PATH" in os.environ:
        return os.environ["WHEELSAVER_DB_PATH"]

    # 2. Proyecto local (desarrollo)
    local_db = os.path.join(os.getcwd(), "data", "top_repos.db")
    if os.path.exists(local_db):
        return local_db

    # 3. Instalación global (fallback)
    return os.path.join(os.path.expanduser("~"), ".wheelsaver", "top_repos.db")


DB_PATH = get_db_path()


def make_repo_id(owner, name):
    """
    Genera un ID sintetico consistente para repos sin GitHub node ID.
    Usa SHA-256 de 'owner/name' -> 16 chars hex.
    """
    raw = f"{owner.lower()}/{name.lower()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def escape_fts_query(kw: str) -> str:
    """Escapa comillas dobles internas y remueve operadores especiales de FTS5."""
    kw_clean = re.sub(r'[*():^"=]', " ", str(kw))
    return kw_clean.strip()


_DB_INITIALIZED = False


def init_db():
    global _DB_INITIALIZED
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    if not os.path.exists(DB_PATH):
        seed_db = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "top_repos.db")
        if os.path.exists(seed_db):
            shutil.copy2(seed_db, DB_PATH)
            logger.info("Copied seed DB from {} to {}", seed_db, DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS repos (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            owner TEXT NOT NULL,
            description TEXT DEFAULT '',
            url TEXT NOT NULL,
            stars INTEGER NOT NULL,
            language TEXT DEFAULT '',
            topics TEXT DEFAULT '',
            updated_at TEXT DEFAULT '',
            is_archived INTEGER DEFAULT 0
        )
    """)

    # Columnas legacy (para BDs creadas antes de que existieran)
    for col in ["is_archived"]:
        try:
            cursor.execute(f"ALTER TABLE repos ADD COLUMN {col} INTEGER DEFAULT 0")
        except sqlite3.OperationalError as e:
            if "duplicate" not in str(e).lower():
                logger.warning("Error agregando columna legacy {}: {}", col, e)

    # Crear tabla de metadatos de ejecución
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS run_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            repos_before INTEGER DEFAULT 0,
            repos_after INTEGER DEFAULT 0,
            repos_inserted INTEGER DEFAULT 0,
            repos_filtered INTEGER DEFAULT 0,
            min_stars_scanned INTEGER DEFAULT 500,
            status TEXT DEFAULT 'running'
        )
    """)

    # Índices para búsquedas rápidas (IGNORE si ya existen)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_repos_stars ON repos(stars DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_repos_language ON repos(language)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_repos_owner ON repos(owner)")

    # FTS5 para búsqueda full-text
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS repos_fts USING fts5(
            name, description, topics,
            content='repos',
            content_rowid='rowid'
        )
    """)

    # Crear triggers FTS5 incrementales (solo si no existen)
    if not _DB_INITIALIZED:
        try:
            cursor.executescript("""
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
            _DB_INITIALIZED = True
        except sqlite3.OperationalError as e:
            # Los triggers FTS5 ya existen en esta BD (idempotencia)
            logger.debug("Triggers FTS5 ya creados: {}", e)

    conn.commit()
    return conn


def rebuild_fts():
    """Reconstruye el índice FTS5 desde los datos actuales de repos."""
    conn = init_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO repos_fts(repos_fts) VALUES('rebuild')")
        conn.commit()
        logger.info("Indice FTS5 reconstruido")
    except Exception as e:
        logger.error("Error al reconstruir indice FTS5: {}", e)
    finally:
        conn.close()


def upsert_repos(repos_list, conn=None):
    """
    Inserts or updates a list of repositories in the database.
    Uses executemany for bulk insert performance.
    """
    owns_conn = False
    if conn is None:
        conn = init_db()
        owns_conn = True
    try:
        cursor = conn.cursor()

        data = []
        for repo in repos_list:
            topics_str = ",".join(repo.get("topics", []))
            data.append(
                (
                    repo["id"],
                    repo["name"],
                    repo["owner"],
                    repo.get("description", ""),
                    repo["url"],
                    repo["stars"],
                    repo.get("language", ""),
                    topics_str,
                    repo.get("updated_at", ""),
                )
            )

        cursor.executemany(
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

        conn.commit()

        # Sync FTS5 via triggers AFTER INSERT — no rebuild manual
    finally:
        if owns_conn:
            conn.close()


def upsert_external_repos(repos_list, conn=None):
    """
    Como upsert_repos pero genera automaticamente un ID sintetico
    a partir de (owner, name) para fuentes externas que no tienen
    el GitHub node ID (EvanLi, gitstar-ranking, etc.).
    """
    for repo in repos_list:
        if "id" not in repo or not repo["id"]:
            repo["id"] = make_repo_id(repo["owner"], repo["name"])
    upsert_repos(repos_list, conn=conn)


def get_stats(conn=None):
    """Devuelve estadísticas de la base de datos."""
    owns_conn = False
    if conn is None:
        conn = init_db()
        owns_conn = True
    try:
        cursor = conn.cursor()
        stats = {}
        cursor.execute("SELECT COUNT(*) FROM repos")
        stats["total_repos"] = cursor.fetchone()[0]

        cursor.execute("SELECT MIN(stars), MAX(stars), AVG(stars) FROM repos")
        row = cursor.fetchone()
        stats["stars_min"] = row[0]
        stats["stars_max"] = row[1]
        stats["stars_avg"] = round(row[2]) if row[2] else 0

        cursor.execute('SELECT COUNT(DISTINCT language) FROM repos WHERE language IS NOT NULL AND language != ""')
        stats["languages"] = cursor.fetchone()[0]

        cursor.execute("""
            SELECT language, COUNT(*) as cnt FROM repos
            WHERE language IS NOT NULL AND language != "" GROUP BY language ORDER BY cnt DESC LIMIT 10
        """)
        stats["top_languages"] = {r[0]: r[1] for r in cursor.fetchall()}
    finally:
        if owns_conn:
            conn.close()
    return stats


# ──────────────────────────────────────────────────────────────────────────────
# Re-export de búsqueda (backward-compatibilidad de imports)
#   from scraper.db_manager import search_repos, calculate_repo_score, ...
# Se coloca al final para evitar import circular (scraper/search importa
# init_db y upsert_repos de este módulo).
# ──────────────────────────────────────────────────────────────────────────────
