"""
import_from_evanli.py — Importa repos desde EvanLi/Github-Ranking

Fuente: https://github.com/EvanLi/Github-Ranking
Contiene Top 100 diarios por lenguaje en formato Markdown.
Se actualiza a diario via GitHub Actions.

Uso:
    python scripts/import_from_evanli.py
    python cli.py import evanli
"""

import re
import sys
import os
import time

import httpx
from tqdm import tqdm
from loguru import logger

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scraper.db_manager import upsert_external_repos, get_stats

RAW_BASE = "https://raw.githubusercontent.com/EvanLi/Github-Ranking/master"

ARCHIVOS = [
    "Top100/Top-100-stars.md",
    "Top100/Top-100-forks.md",
    "Top100/ActionScript.md",
    "Top100/C.md",
    "Top100/CPP.md",
    "Top100/CSS.md",
    "Top100/CSharp.md",
    "Top100/Clojure.md",
    "Top100/CoffeeScript.md",
    "Top100/DM.md",
    "Top100/Dart.md",
    "Top100/Elixir.md",
    "Top100/Go.md",
    "Top100/Groovy.md",
    "Top100/HTML.md",
    "Top100/Haskell.md",
    "Top100/Java.md",
    "Top100/JavaScript.md",
    "Top100/Julia.md",
    "Top100/Kotlin.md",
    "Top100/Lua.md",
    "Top100/MATLAB.md",
    "Top100/Objective-C.md",
    "Top100/PHP.md",
    "Top100/Perl.md",
    "Top100/PowerShell.md",
    "Top100/Python.md",
    "Top100/R.md",
    "Top100/Ruby.md",
    "Top100/Rust.md",
    "Top100/Scala.md",
    "Top100/Shell.md",
    "Top100/Swift.md",
    "Top100/TeX.md",
    "Top100/TypeScript.md",
    "Top100/Vim-script.md",
]


def parse_md_table(text):
    """
    Parsea la tabla Markdown de EvanLi.

    Formato:
    | # | [name](url) | stars | forks | language | issues | description | last_commit |
    """
    repos = []
    seen = set()

    pattern = re.compile(
        r"\|\s*\d+\s*\|"
        r"\s*\[([^\]]+)\]\(([^)]+)\)\s*\|"  # name + url
        r"\s*([\d,]+)\s*\|"  # stars
        r"\s*([\d,]+)\s*\|"  # forks
        r"\s*([^|]*?)\s*\|"  # language
        r"\s*([\d,]+)\s*\|"  # open issues
        r"\s*(.*?)\s*\|"  # description
        r"\s*(.*?)\s*\|"  # last commit
    )

    for line in text.split("\n"):
        line = line.strip()
        m = pattern.match(line)
        if not m:
            continue

        name = m.group(1).strip()
        url = m.group(2).strip()
        stars_str = m.group(3).replace(",", "")
        lang = m.group(5).strip()
        desc = m.group(7).strip()
        updated_at = m.group(8).strip()

        key = name.lower()
        if key in seen:
            continue
        seen.add(key)

        owner = ""
        try:
            parts = url.rstrip("/").split("/")
            if len(parts) >= 4 and parts[2] == "github.com":
                owner = parts[3]
        except Exception:
            pass

        if not owner:
            continue

        try:
            stars = int(stars_str)
        except ValueError:
            continue

        repos.append(
            {
                "name": name,
                "owner": owner,
                "description": desc,
                "url": url,
                "stars": stars,
                "language": lang if lang and lang != "None" else "",
                "topics": [],
                "updated_at": updated_at,
            }
        )

    return repos


def fetch_and_parse(url, label, client):
    """Descarga un archivo Markdown y parsea los repos."""
    try:
        resp = client.get(url)
        resp.raise_for_status()
        repos = parse_md_table(resp.text)
        return repos
    except httpx.RequestError as e:
        logger.error("Error conexion {}: {}", label, e)
        return []
    except httpx.HTTPStatusError as e:
        logger.warning("HTTP {} en {}", e.response.status_code, label)
        return []


def main():
    logger.info("Importando desde EvanLi/Github-Ranking ({} archivos)", len(ARCHIVOS))

    antes = get_stats()
    todos = []

    with httpx.Client(timeout=30.0) as client:
        for archivo in tqdm(ARCHIVOS, desc="EvanLi", unit="archivo"):
            url = f"{RAW_BASE}/{archivo}"
            label = archivo.replace("Top100/", "").replace(".md", "")
            repos = fetch_and_parse(url, label, client)
            todos.extend(repos)
            time.sleep(0.3)

    # Deduplicar
    unicos = {}
    for r in todos:
        key = r["name"].lower()
        if key not in unicos or len(r["description"]) > len(unicos[key]["description"]):
            unicos[key] = r

    final = list(unicos.values())
    print(f"\nTotal crudo: {len(todos)} | Despues de dedup: {len(final)}")

    if not final:
        logger.warning("No se encontraron repos en EvanLi")
        return

    BATCH = 100
    for i in range(0, len(final), BATCH):
        batch = final[i : i + BATCH]
        upsert_external_repos(batch)

    despues = get_stats()
    logger.info(
        "EvanLi: antes={} despues={} nuevos={}",
        antes["total_repos"],
        despues["total_repos"],
        despues["total_repos"] - antes["total_repos"],
    )


if __name__ == "__main__":
    main()
