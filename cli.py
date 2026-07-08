#!/usr/bin/env python3
"""
WheelSaver CLI — Punto de entrada unificado para WheelSaver.

Uso:
    python cli.py search <keywords...> [--limit N] [--language L] [--min-stars N]
    python cli.py stats
    python cli.py scrape [--min-stars N]
    python cli.py import evanli
    python cli.py import gitstar [--pages N] [--start N]
    python cli.py api [--host H] [--port P]
"""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule

app = typer.Typer(
    name="wheelsaver",
    help="WheelSaver — GitHub repo scraper, search & audit tool",
    no_args_is_help=True,
)
import_group = typer.Typer(help="Import data from external sources")
app.add_typer(import_group, name="import")

console = Console()


@app.command()
def search(
    keywords: list[str] = typer.Argument(
        ..., help="Keywords para buscar (FTS5 sobre name, description, topics)"
    ),
    limit: int = typer.Option(20, "--limit", "-l", help="Max resultados"),
    language: str = typer.Option(
        None, "--language", help="Filtrar por lenguaje (ej: Python, Rust)"
    ),
    min_stars: int = typer.Option(
        None, "--min-stars", help="Estrellas minimas"
    ),
):
    """Busca repos en la base de datos usando FTS5."""
    from scraper.db_manager import search_repos_multi_keywords

    results = search_repos_multi_keywords(keywords, limit=limit * 3)

    # Filtros post-query
    if language:
        results = [r for r in results if r["language"].lower() == language.lower()]
    if min_stars:
        results = [r for r in results if r["stars"] >= min_stars]

    results = results[:limit]

    if not results:
        console.print("[yellow]No se encontraron repositorios.[/yellow]")
        raise typer.Exit()

    table = Table(
        title=f"Resultados para: {' '.join(keywords)}",
        caption=f"{len(results)} repos mostrados",
    )
    table.add_column("Nombre", style="cyan", no_wrap=True)
    table.add_column("Owner", style="green")
    table.add_column("Estrellas", justify="right", style="bold yellow")
    table.add_column("Lenguaje", style="magenta")
    table.add_column("Descripcion", no_wrap=False)

    for r in results:
        desc = (r["description"][:80] + "...") if r["description"] and len(r["description"]) > 80 else (r["description"] or "")
        table.add_row(
            r["name"], r["owner"], f'{r["stars"]:,}',
            r["language"] or "-", desc
        )

    console.print(table)


@app.command()
def stats():
    """Muestra estadisticas de la base de datos."""
    from scraper.db_manager import get_stats

    s = get_stats()

    panel = Panel(
        f"[bold]Total repos:[/bold] {s['total_repos']:,}\n"
        f"[bold]Lenguajes:[/bold] {s['languages']}\n"
        f"[bold]Estrellas:[/bold] "
        f"min [green]{s['stars_min']:,}[/green] / "
        f"max [yellow]{s['stars_max']:,}[/yellow] / "
        f"avg [cyan]{s['stars_avg']:,}[/cyan]",
        title="WheelSaver DB Stats",
        border_style="blue",
    )
    console.print(panel)

    if s.get("top_languages"):
        table = Table("Lenguaje", "Repos", title="Top 10 Lenguajes")
        for lang, cnt in s["top_languages"].items():
            table.add_row(lang, f"{cnt:,}")
        console.print(table)


@app.command()
def scrape(
    min_stars: int = typer.Option(
        500, "--min-stars", help="Umbral minimo de estrellas"
    ),
):
    """Ejecuta el scraper de GitHub GraphQL (barre desde Top 1 hacia abajo)."""
    from scraper.github_fetcher import fetch_top_repos

    console.print(f"[bold blue]Iniciando scraper GraphQL...[/bold blue]")
    fetch_top_repos(min_stars=min_stars)


@import_group.command(name="evanli")
def import_evanli():
    """Importa Top 100 por lenguaje desde EvanLi/Github-Ranking."""
    from scripts.import_from_evanli import main as evanli_main

    console.print("[bold blue]Importando desde EvanLi/Github-Ranking...[/bold blue]")
    evanli_main()
    console.print("[bold green]Importacion EvanLi completada.[/bold green]")


@import_group.command(name="gitstar")
def import_gitstar(
    pages: int = typer.Option(
        0, "--pages", "-p", help="Numero de paginas (0 = todas, max 100)"
    ),
):
    """Scrapea gitstar-ranking.com para rankings de repos."""
    import sys
    import scripts.scrape_gitstar_ranking as gs

    console.print("[bold blue]Scrapeando gitstar-ranking.com...[/bold blue]")

    # Guardar args originales y poner los nuestros
    old_argv = sys.argv
    args = ["scrape_gitstar_ranking.py", f"--pages={pages}"] if pages else ["scrape_gitstar_ranking.py"]
    sys.argv = args
    try:
        gs.main()
    finally:
        sys.argv = old_argv
    console.print("[bold green]Scrapeo gitstar-ranking completado.[/bold green]")


@app.command()
def api(
    host: str = typer.Option("0.0.0.0", "--host", help="Direccion de escucha"),
    port: int = typer.Option(8000, "--port", "-p", help="Puerto"),
):
    """Lanza el servidor FastAPI con la API REST."""
    import uvicorn

    console.print(f"[bold blue]Lanzando API en http://{host}:{port}[/bold blue]")
    console.print("[dim]Documentacion: http://localhost:" + str(port) + "/docs[/dim]")
    uvicorn.run("api.main:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    app()
