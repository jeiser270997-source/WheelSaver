"""
scrape_gitstar_ranking.py — Scrapea gitstar-ranking.com/repositories

Fuente: https://gitstar-ranking.com/repositories
Ranking global de GitHub repos ordenados por estrellas.
~100 paginas x 50 repos = ~5,000 repos escaneables.

Uso:
    python scripts/scrape_gitstar_ranking.py              # todas las paginas
    python scripts/scrape_gitstar_ranking.py --pages 5    # solo primeras 5
    python scripts/scrape_gitstar_ranking.py --start 50   # desde la pagina 50
"""

import sys
import os
import re
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scraper.db_manager import upsert_external_repos, get_stats

TOTAL_PAGES = 100
REPOS_PER_PAGE = 50
BASE_URL = "https://gitstar-ranking.com/repositories"
REQUEST_DELAY = 1.5  # segundos entre paginas para no saturar


def parse_repos_from_html(html):
    """Extrae repos del HTML de una pagina de gitstar-ranking."""
    repos = []
    seen = set()

    # Buscar cada entrada: <a class="list-group-item paginated_item" href="/owner/repo">
    pattern = re.compile(
        r'<a\s+class="list-group-item\s*paginated_item"[^>]*href="/([^"/]+/[^"/]+)"[^>]*>'
        r'(.*?)'
        r'</a>',
        re.DOTALL,
    )

    for m in pattern.finditer(html):
        owner_repo = m.group(0)
        href_owner_repo = m.group(1)
        inner = m.group(2)

        # Parse owner/repo from href
        if "/" not in href_owner_repo:
            continue
        owner, name = href_owner_repo.split("/", 1)

        key = f"{owner.lower()}/{name.lower()}"
        if key in seen:
            continue
        seen.add(key)

        # Stars: <span class="stargazers_count">\d+([,\.]\d+)*</span>
        stars_match = re.search(
            r'stargazers_count[^>]*>\s*(?:<i[^>]*></i>\s*)?([\d,]+)\s*<',
            inner,
        )
        stars = 0
        if stars_match:
            stars = int(stars_match.group(1).replace(",", ""))

        # Description: <div class="repo-description" title="...">
        desc_match = re.search(
            r'repo-description["\'][^>]*title\s*=\s*["\']([^"\']*)["\']',
            inner,
        )
        description = desc_match.group(1).strip() if desc_match else ""

        # Language: <div class="repo-language"><span class="label label-default">...</span>
        lang_match = re.search(
            r'repo-language[^>]*>.*?label[^>]*>\s*([^<]+?)\s*<', inner, re.DOTALL
        )
        language = ""
        if lang_match:
            lang_text = lang_match.group(1).strip()
            if lang_text != "No language available":
                language = lang_text

        repos.append(
            {
                "name": name,
                "owner": owner,
                "description": description,
                "url": f"https://github.com/{owner}/{name}",
                "stars": stars,
                "language": language,
                "topics": [],
                "updated_at": "",
            }
        )

    return repos


def scrape_gitstar(start_page=1, max_pages=None):
    """Scrapea gitstar-ranking.com desde start_page hasta max_pages."""
    total_pages = max_pages if max_pages else (TOTAL_PAGES - start_page + 1)

    print(f"Scrapeando gitstar-ranking.com: pagina {start_page} a {start_page + total_pages - 1}")
    print(f"  Total estimado: {total_pages * REPOS_PER_PAGE} repos\n")

    all_repos = []
    page = start_page
    consecutive_errors = 0

    while page < start_page + total_pages and page <= TOTAL_PAGES:
        url = BASE_URL if page == 1 else f"{BASE_URL}?page={page}"

        try:
            import requests

            resp = requests.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
                timeout=30,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            consecutive_errors += 1
            wait = min(30, consecutive_errors * 5)
            print(f"  Error pagina {page}: {e}. Esperando {wait}s...")
            time.sleep(wait)
            if consecutive_errors > 3:
                print("  Demasiados errores consecutivos. Abortando.")
                break
            continue

        consecutive_errors = 0

        repos = parse_repos_from_html(resp.text)
        all_repos.extend(repos)

        print(f"  Pagina {page:3d}: {len(repos):2d} repos extraidos (total: {len(all_repos):,})")

        page += 1
        time.sleep(REQUEST_DELAY)

    return all_repos


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Scrapea gitstar-ranking.com para alimentar WheelSaver"
    )
    parser.add_argument("--pages", type=int, default=0, help="Numero de paginas a scrapear (0 = todas)")
    parser.add_argument("--start", type=int, default=1, help="Pagina inicial (default: 1)")
    args = parser.parse_args()

    print("=" * 60)
    print("  gitstar-ranking.com — Scraper")
    print("=" * 60)

    antes = get_stats()
    print(f"\nRepos antes de la importacion: {antes['total_repos']:,}\n")

    max_pages = args.pages if args.pages > 0 else None
    todos = scrape_gitstar(start_page=args.start, max_pages=max_pages)

    if not todos:
        print("No se extrajeron repos. Abortando.")
        return

    # Deduplicar por (owner, name)
    unicos = {}
    for r in todos:
        key = f"{r['owner'].lower()}/{r['name'].lower()}"
        if key not in unicos or r["stars"] > unicos[key]["stars"]:
            unicos[key] = r

    final = list(unicos.values())
    print(f"\nTotal crudo: {len(todos)} | Despues de dedup: {len(final)}")

    # Importar en batches
    BATCH = 100
    for i in range(0, len(final), BATCH):
        batch = final[i : i + BATCH]
        upsert_external_repos(batch)
        print(f"  Batch {i//BATCH + 1}: {len(batch)} repos insertados/actualizados")

    despues = get_stats()
    print(f"\nResumen final:")
    print(f"  Antes:   {antes['total_repos']:,} repos")
    print(f"  Despues: {despues['total_repos']:,} repos")
    print(f"  Nuevos:  {despues['total_repos'] - antes['total_repos']:,}")
    print(f"  Listo!")


if __name__ == "__main__":
    main()
