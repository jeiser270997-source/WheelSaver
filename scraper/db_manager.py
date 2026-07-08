import sqlite3
import os
import hashlib
from loguru import logger

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "top_repos.db")


def make_repo_id(owner, name):
    """
    Genera un ID sintetico consistente para repos sin GitHub node ID.
    Usa SHA-256 de 'owner/name' -> 16 chars hex.
    """
    raw = f"{owner.lower()}/{name.lower()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS repos (
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

    # Columnas legacy (para BDs creadas antes de que existieran)
    for col in ["is_archived"]:
        try:
            cursor.execute(f"ALTER TABLE repos ADD COLUMN {col} INTEGER DEFAULT 0")
        except Exception:
            pass

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


def upsert_repos(repos_list):
    """
    Inserts or updates a list of repositories in the database.
    repos_list is a list of dictionaries.
    """
    conn = init_db()
    cursor = conn.cursor()

    for repo in repos_list:
        topics_str = ",".join(repo.get("topics", []))
        cursor.execute(
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
            ),
        )

    conn.commit()

    # Sincronizar FTS después de inserts batch
    try:
        cursor.execute("INSERT INTO repos_fts(repos_fts) VALUES('rebuild')")
        conn.commit()
    except Exception:
        pass

    conn.close()


def upsert_external_repos(repos_list):
    """
    Como upsert_repos pero genera automaticamente un ID sintetico
    a partir de (owner, name) para fuentes externas que no tienen
    el GitHub node ID (EvanLi, gitstar-ranking, etc.).
    """
    for repo in repos_list:
        if "id" not in repo or not repo["id"]:
            repo["id"] = make_repo_id(repo["owner"], repo["name"])
    upsert_repos(repos_list)


def search_repos(keyword, limit=5):
    """
    Busca repos usando FTS5 (full-text search).
    Si FTS5 falla (poco probable), hace fallback a LIKE.
    """
    conn = init_db()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT r.name, r.owner, r.description, r.url, r.stars, r.language, r.topics
            FROM repos_fts f
            JOIN repos r ON r.rowid = f.rowid
            WHERE repos_fts MATCH ?
            ORDER BY r.stars DESC
            LIMIT ?
        """,
            (keyword, limit),
        )
    except sqlite3.OperationalError:
        # Fallback: LIKE query
        like_kw = f"%{keyword}%"
        cursor.execute(
            """
            SELECT name, owner, description, url, stars, language, topics
            FROM repos
            WHERE name LIKE ? OR description LIKE ? OR topics LIKE ?
            ORDER BY stars DESC
            LIMIT ?
        """,
            (like_kw, like_kw, like_kw, limit),
        )

    results = cursor.fetchall()
    conn.close()

    repos = []
    for r in results:
        repos.append(
            {
                "name": r[0],
                "owner": r[1],
                "description": r[2],
                "url": r[3],
                "stars": r[4],
                "language": r[5],
                "topics": r[6],
            }
        )
    return repos


def search_repos_multi_keywords(keywords, limit=20):
    """
    Busca repos que matcheen CUALQUIERA de las keywords dadas.
    Usa FTS5 con OR, fallback a LIKE.
    """
    conn = init_db()
    cursor = conn.cursor()

    try:
        fts_query = " OR ".join(keywords)
        cursor.execute(
            """
            SELECT DISTINCT r.name, r.owner, r.description, r.url, r.stars, r.language, r.topics
            FROM repos_fts f
            JOIN repos r ON r.rowid = f.rowid
            WHERE repos_fts MATCH ?
            ORDER BY r.stars DESC
            LIMIT ?
        """,
            (fts_query, limit),
        )
    except sqlite3.OperationalError:
        # Fallback: LIKE queries
        seen = set()
        cursor.execute(
            "SELECT name, owner, description, url, stars, language, topics FROM repos ORDER BY stars DESC"
        )
        all_repos = cursor.fetchall()
        results = []
        for r in all_repos:
            text = f"{r[0]} {r[1]} {r[2] or ''} {r[6] or ''}".lower()
            if any(kw.lower() in text for kw in keywords):
                if r[0] not in seen:
                    seen.add(r[0])
                    results.append(r)
                    if len(results) >= limit:
                        break

    results = cursor.fetchall() if "results" not in dir() else results
    conn.close()

    repos = []
    for r in results:
        repos.append(
            {
                "name": r[0],
                "owner": r[1],
                "description": r[2],
                "url": r[3],
                "stars": r[4],
                "language": r[5],
                "topics": r[6],
            }
        )
    return repos


def get_stats():
    """Devuelve estadísticas de la base de datos."""
    conn = init_db()
    cursor = conn.cursor()
    stats = {}
    cursor.execute("SELECT COUNT(*) FROM repos")
    stats["total_repos"] = cursor.fetchone()[0]

    cursor.execute("SELECT MIN(stars), MAX(stars), AVG(stars) FROM repos")
    row = cursor.fetchone()
    stats["stars_min"] = row[0]
    stats["stars_max"] = row[1]
    stats["stars_avg"] = round(row[2]) if row[2] else 0

    cursor.execute('SELECT COUNT(DISTINCT language) FROM repos WHERE language != ""')
    stats["languages"] = cursor.fetchone()[0]

    cursor.execute("""
        SELECT language, COUNT(*) as cnt FROM repos
        WHERE language != "" GROUP BY language ORDER BY cnt DESC LIMIT 10
    """)
    stats["top_languages"] = {r[0]: r[1] for r in cursor.fetchall()}

    conn.close()
    return stats


def get_all_repos():
    conn = init_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name, description, topics, url, stars FROM repos ORDER BY stars DESC")
    results = cursor.fetchall()
    conn.close()
    return results
