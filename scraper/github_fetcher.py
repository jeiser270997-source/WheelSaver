import os
import sqlite3
import httpx
import time
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from loguru import logger
from scraper.db_manager import upsert_repos, DB_PATH, init_db

load_dotenv(override=True)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# ============================================================
# UMBRAL DE CALIDAD (repos de 500-1000 estrellas)
# Se aplican filtros extra para no guardar repos desatendidos
# ============================================================
QUALITY_FILTER_THRESHOLD = 1000  # por debajo aplicamos filtros
MAX_INACTIVE_DAYS = 365  # sin commits en >1 año = desatendido


def is_active_repo(updated_at_str, stars):
    """
    Repos con +1000 estrellas: siempre se incluyen.
    Repos con 500-999 estrellas: solo si tuvieron commits en el último año.
    """
    if stars >= QUALITY_FILTER_THRESHOLD:
        return True

    try:
        updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=MAX_INACTIVE_DAYS)
        return updated_at >= cutoff_date
    except Exception:
        return False


def log_run_start():
    """Registra el inicio de una ejecución en run_history y devuelve el run_id."""
    conn = init_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM repos")
    repos_before = c.fetchone()[0]
    c.execute(
        "INSERT INTO run_history (started_at, repos_before, status) VALUES (?, ?, 'running')",
        (datetime.now(timezone.utc).isoformat(), repos_before),
    )
    run_id = c.lastrowid
    conn.commit()
    conn.close()
    return run_id, repos_before


def log_run_finish(run_id, repos_inserted, repos_filtered, min_stars, status="completed"):
    """Registra la finalización de una ejecución en run_history."""
    conn = init_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM repos")
    repos_after = c.fetchone()[0]
    c.execute(
        """UPDATE run_history
           SET finished_at = ?, repos_after = ?, repos_inserted = ?,
               repos_filtered = ?, min_stars_scanned = ?, status = ?
           WHERE id = ?""",
        (
            datetime.now(timezone.utc).isoformat(),
            repos_after,
            repos_inserted,
            repos_filtered,
            min_stars,
            status,
            run_id,
        ),
    )
    conn.commit()
    conn.close()


def fetch_top_repos(min_stars=500):
    """
    Escanea GitHub desde el Top 1 (repos con más estrellas) hacia abajo
    hasta alcanzar el umbral minimo de estrellas.

    En producción SIEMPRE empieza desde arriba para refrescar la data
    de los repos existentes (upsert), no solo agregar nuevos.
    """
    if not GITHUB_TOKEN:
        print("❌ Error: GITHUB_TOKEN no encontrado en .env")
        return

    url = "https://api.github.com/graphql"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json",
    }

    query = """
    query($queryString: String!, $cursor: String) {
      search(query: $queryString, type: REPOSITORY, first: 100, after: $cursor) {
        pageInfo { endCursor hasNextPage }
        edges {
          node {
            ... on Repository {
              id name isArchived owner { login } description url stargazerCount
              primaryLanguage { name }
              repositoryTopics(first: 10) { nodes { topic { name } } }
              updatedAt
            }
          }
        }
      }
    }
    """

    run_id, repos_before = log_run_start()
    logger.info(
        "Iniciando escaneo desde Top 1 hasta {} estrellas (repos actuales: {})",
        min_stars,
        repos_before,
    )

    current_max_stars = 9999999  # Siempre desde el Top 1 en producción
    total_fetched = 0
    total_skipped = 0
    consecutive_errors = 0

    try:
        while current_max_stars >= min_stars:
            query_string = f"stars:<={current_max_stars} stars:>={min_stars} sort:stars-desc"
            cursor = None
            has_next_page = True
            last_repo_stars = current_max_stars

            while has_next_page:
                variables = {"queryString": query_string, "cursor": cursor}

                try:
                    with httpx.Client(timeout=httpx.Timeout(30.0, connect=15.0)) as client:
                        response = client.post(
                            url,
                            headers=headers,
                            json={"query": query, "variables": variables},
                        )
                except httpx.RequestError as e:
                    consecutive_errors += 1
                    wait = min(60, consecutive_errors * 5)
                    logger.warning("Error de conexion: {} (intento {})", e, consecutive_errors)
                    time.sleep(wait)
                    if consecutive_errors > 5:
                        logger.error("Demasiados errores consecutivos, abortando")
                        raise
                    continue

                consecutive_errors = 0  # Reset al tener éxito

                if response.status_code == 403:
                    logger.warning("Rate-limit de GitHub alcanzado. Esperando 60s...")
                    time.sleep(60)
                    continue
                elif response.status_code != 200:
                    wait = min(30, response.status_code * 2)
                    logger.warning("HTTP {} recibido. Esperando {}s...", response.status_code, wait)
                    time.sleep(wait)
                    continue

                data = response.json()
                if "errors" in data:
                    for err in data["errors"]:
                        logger.error("GraphQL error: {}", err.get("message", "desconocido"))
                    time.sleep(10)
                    continue

                search_data = data["data"]["search"]
                edges = search_data["edges"]

                if not edges:
                    break

                repos_to_insert = []
                for edge in edges:
                    node = edge["node"]
                    stars = node["stargazerCount"]
                    last_repo_stars = stars

                    # Filtro 1: Archivados
                    if node.get("isArchived", False):
                        total_skipped += 1
                        continue

                    # Filtro 2: 500-999 estrellas sin actividad reciente
                    if not is_active_repo(node["updatedAt"], stars):
                        total_skipped += 1
                        continue

                    topics = (
                        [
                            t["topic"]["name"]
                            for t in node.get("repositoryTopics", {}).get("nodes", [])
                        ]
                        if node.get("repositoryTopics")
                        else []
                    )

                    lang = node.get("primaryLanguage")
                    repos_to_insert.append(
                        {
                            "id": node["id"],
                            "name": node["name"],
                            "owner": node["owner"]["login"],
                            "description": node["description"],
                            "url": node["url"],
                            "stars": stars,
                            "language": lang.get("name", "") if lang else "",
                            "topics": topics,
                            "updated_at": node["updatedAt"],
                        }
                    )

                if repos_to_insert:
                    upsert_repos(repos_to_insert)
                    total_fetched += len(repos_to_insert)

                print(
                    f"✅ Procesados: {total_fetched:,} | "
                    f"Omitidos: {total_skipped:,} | "
                    f"Estrellas actuales: {last_repo_stars:,}"
                )

                has_next_page = search_data["pageInfo"]["hasNextPage"]
                cursor = search_data["pageInfo"]["endCursor"]
                time.sleep(0.5)  # Respetar rate-limit de GitHub

            # GitHub GraphQL devuelve max 1000 resultados por búsqueda.
            # Ajustamos el techo para la siguiente iteración.
            current_max_stars = last_repo_stars - 1

    except KeyboardInterrupt:
        logger.warning("Proceso interrumpido por el usuario")
        log_run_finish(run_id, total_fetched, total_skipped, min_stars, status="interrupted")
        return
    except Exception as e:
        logger.error("Error fatal: {}", e)
        log_run_finish(run_id, total_fetched, total_skipped, min_stars, status="failed")
        return

    log_run_finish(run_id, total_fetched, total_skipped, min_stars, status="completed")
    logger.info(
        "Escaneo completado: {} insertados, {} filtrados, {} total en BD",
        total_fetched,
        total_skipped,
        total_fetched + repos_before,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="WheelSaver Scraper — Descarga repos top de GitHub con filtros de calidad"
    )
    parser.add_argument(
        "--min-stars", type=int, default=500, help="Mínimo de estrellas (default: 500)"
    )
    args = parser.parse_args()
    fetch_top_repos(min_stars=args.min_stars)
