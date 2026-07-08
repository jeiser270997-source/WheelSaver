"""
scrape_gitstar_ranking.py — Scrapea gitstar-ranking.com/repositories

Fuente: https://gitstar-ranking.com/repositories
Ranking global de GitHub repos ordenados por estrellas.
~100 paginas x 50 repos = ~5,000 repos escaneables.

Uso:
    python scripts/scrape_gitstar_ranking.py              # todas las paginas
    python scripts/scrape_gitstar_ranking.py --pages 5    # solo primeras 5
    python scripts/scrape_gitstar_ranking.py --start 50   # desde la pagina 50
    python cli.py import gitstar [--pages N]
"""

import sys
import os
import re
import time

import httpx
from tqdm import tqdm
from loguru import logger

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scraper.db_manager import upsert_external_repos, get_stats

TOTAL_PAGES = 100
REPOS_PER_PAGE = 50
BASE_URL = "https://gitstar-ranking.com/repositories"
REQUEST_DELAY = 1.5


def parse_repos_from_html(html):
    """Extrae repos del HTML de una pagina de gitstar-ranking."""
    repos = []
    seen = set()

    pattern = re.compile(
        r'<a\s+class="list-group-item\s*paginated_item"[^>]*href="/([^"/]+/[^"/]+)"[^>]*>'
        r"(.*?)"
        r"</a>",
        re.DOTALL,
    )

    for m in pattern.finditer(html):
        href_owner_repo = m.group(1)
        inner = m.group(2)

        if "/" not in href_owner_repo:
            continue
        owner, name = href_owner_repo.split("/", 1)

        key = f"{owner.lower()}/{name.lower()}"
        if key in seen:
            continue
        seen.add(key)

        stars_match = re.search(
            r"stargazers_count[^>]*>\s*(?:<i[^>]*></i>\s*)?([\d,]+)\s*<",
            inner,
        )
        stars = int(stars_match.group(1).replace(",", "")) if stars_match else 0

        desc_match = re.search(
            r'repo-description["\'][^>]*title\s*=\s*["\']([^"\']*)["\']',
            inner,
        )
        description = desc_match.group(1).strip() if desc_match else ""

        lang_match = re.search(
            r"repo-language[^>]*>.*?label[^>]*>\s*([^<]+?)\s*<", inner, re.DOTALL
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

    logger.info(
        "Scrapeando gitstar-ranking.com: paginas {} a {}", start_page, start_page + total_pages - 1
    )

    all_repos = []
    page = start_page
    consecutive_errors = 0

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    with httpx.Client(timeout=30.0, headers=headers) as client:
        pages_range = range(page, min(page + total_pages, TOTAL_PAGES + 1))

        for page_num in tqdm(pages_range, desc="gitstar-ranking", unit="pag"):
            url = BASE_URL if page_num == 1 else f"{BASE_URL}?page={page_num}"

            try:
                resp = client.get(url)
                resp.raise_for_status()
            except httpx.RequestError as e:
                consecutive_errors += 1
                wait = min(30, consecutive_errors * 5)
                logger.warning(
                    "Error pagina {}: {} (esperando {}s, intento {})",
                    page_num,
                    e,
                    wait,
                    consecutive_errors,
                )
                time.sleep(wait)
                if consecutive_errors > 3:
                    logger.error("Demasiados errores en gitstar, abortando")
                    break
                continue
            except httpx.HTTPStatusError as e:
                logger.warning("HTTP {} en pagina {}", e.response.status_code, page_num)
                time.sleep(5)
                continue

            consecutive_errors = 0
            repos = parse_repos_from_html(resp.text)
            all_repos.extend(repos)
            time.sleep(REQUEST_DELAY)

    return all_repos


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Scrapea gitstar-ranking.com")
    parser.add_argument("--pages", type=int, default=0, help="Paginas (0 = todas)")
    parser.add_argument("--start", type=int, default=1, help="Pagina inicial")
    args = parser.parse_args()

    logger.info("Scrapeando gitstar-ranking.com")
    antes = get_stats()

    max_pages = args.pages if args.pages > 0 else None
    todos = scrape_gitstar(start_page=args.start, max_pages=max_pages)

    if not todos:
        logger.warning("No se extrajeron repos de gitstar")
        return

    unicos = {}
    for r in todos:
        key = f"{r['owner'].lower()}/{r['name'].lower()}"
        if key not in unicos or r["stars"] > unicos[key]["stars"]:
            unicos[key] = r

    final = list(unicos.values())
    logger.info("Gitstar: {} crudos, {} unicos", len(todos), len(final))

    BATCH = 100
    for i in range(0, len(final), BATCH):
        batch = final[i : i + BATCH]
        upsert_external_repos(batch)

    despues = get_stats()
    logger.info(
        "Gitstar: antes={} despues={} nuevos={}",
        antes["total_repos"],
        despues["total_repos"],
        despues["total_repos"] - antes["total_repos"],
    )


if __name__ == "__main__":
    main()
