from loguru import logger

from scraper.db_manager import get_db_path, init_db, rebuild_fts


def deduplicate_database():
    db_path = get_db_path()
    logger.info(f"Iniciando deduplicación en: {db_path}")

    conn = init_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM repos")
    before_count = cursor.fetchone()[0]

    # Conserva la fila preferida (Node ID mas largo / mayor numero de estrellas)
    cursor.execute("""
        DELETE FROM repos
        WHERE rowid NOT IN (
            SELECT rowid FROM (
                SELECT rowid,
                       ROW_NUMBER() OVER (
                           PARTITION BY LOWER(owner), LOWER(name)
                           ORDER BY LENGTH(id) DESC, stars DESC, updated_at DESC
                       ) as rn
                FROM repos
            ) WHERE rn = 1
        )
    """)
    deleted_count = cursor.rowcount
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM repos")
    after_count = cursor.fetchone()[0]

    logger.info(f"Deduplicación completada: {before_count} -> {after_count} repos (Eliminados: {deleted_count})")

    # Reconstruir FTS5
    rebuild_fts()
    conn.close()
    return before_count, after_count, deleted_count


if __name__ == "__main__":
    deduplicate_database()
