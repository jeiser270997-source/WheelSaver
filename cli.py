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
    python cli.py ready                            # Checklist de proyecto
    python cli.py swap <feature>                   # Busca alternativa a lo que codeas
    python cli.py audit-code [path]                # bandit + vulture + radon
    python cli.py skillify <repo>                  # Convierte repo en Skill de IA
    python cli.py ask <question>                   # RAG multi-proveedor
"""

import os
import sys

import typer
from rich.panel import Panel
from rich.table import Table

import importlib.util
def _load_cli_commands():
    try:
        from cli_commands.audit import audit_code as _a, ready as _r
        from cli_commands.skills import ask as _ask, skillify as _sk
        from cli_ui import clean as _c, console as _cons
        return _a, _r, _ask, _sk, _c, _cons
    except ModuleNotFoundError:
        # Fallback: añade root del proyecto al path (entry-point global)
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from cli_commands.audit import audit_code as _a2, ready as _r2
        from cli_commands.skills import ask as _ask2, skillify as _sk2
        from cli_ui import clean as _c2, console as _cons2
        return _a2, _r2, _ask2, _sk2, _c2, _cons2

audit_code, ready, ask, skillify, clean, console = _load_cli_commands()

# Reconfigurar stdout/stderr en Windows para evitar UnicodeEncodeError con cp1252
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception as e:
        # Fallback: dejar la codificación por defecto si reconfigure falla
        import logging

        logging.debug("No se pudo reconfigurar stdout/stderr a UTF-8: %s", e)

app = typer.Typer(
    name="wheelsaver",
    help="WheelSaver — GitHub repo scraper, search & audit tool",
    no_args_is_help=True,
)
import_group = typer.Typer(help="Import data from external sources")
app.add_typer(import_group, name="import")



def maybe_update(no_update: bool = False, max_days: int = 7) -> None:
    """Reactivo: si la DB esta desactualizada, la actualiza antes de responder."""
    from scraper.freshness import is_stale

    if no_update:
        return
    try:
        if not is_stale(max_days=max_days):
            return
    except Exception:
        return  # sin DB o error: no bloquear la busqueda
    console.print("[bold yellow]DB desactualizada - actualizando bajo demanda...[/bold yellow]")
    try:
        run_update(pages=2, max_days=max_days, force=True)
        console.print("[bold green]DB actualizada.[/bold green]")
    except Exception as e:
        console.print(f"[red]No se pudo actualizar: {e}[/red]")
        console.print("[dim]Continuando con datos existentes (fallback offline).[/dim]")


@app.command()
def update(
    max_days: int = typer.Option(7, "--max-days", help="Considerar fresca si la DB tiene <= max_days dias"),
    full: bool = typer.Option(False, "--full", help="Scrape GraphQL completo en vez de gitstar incremental"),
    pages: int = typer.Option(3, "--pages", "-p", help="Paginas de gitstar-ranking (incremental, 0 = todas)"),
    force: bool = typer.Option(False, "--force", help="Actualizar aunque la DB este fresca"),
):
    """Actualiza la DB bajo demanda (reactivo). No hace nada si esta fresca."""
    run_update(pages=pages, max_days=max_days, force=force, full=full)


def run_update(pages: int = 3, max_days: int = 7, force: bool = False, full: bool = False) -> None:
    """Implementacion compartida del update reactivo (CLI + hook)."""
    from scraper.db_manager import init_db
    from scraper.freshness import staleness_days
    from scraper.github_fetcher import log_run_finish, log_run_start

    days = staleness_days()
    if not force and days is not None and days <= max_days:
        console.print(f"[green]DB fresca ({days}d <= {max_days}d). Nada que hacer.[/green]")
        return

    conn = init_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM repos")
    before = cur.fetchone()[0]

    run_id, _ = log_run_start()
    try:
        if full:
            from scraper.github_fetcher import fetch_top_repos
            console.print("[bold blue]Scrape GraphQL completo...[/bold blue]")
            fetch_top_repos(min_stars=500, run_id=run_id)
        else:
            import scripts.scrape_gitstar_ranking as gs
            console.print(f"[bold blue]Scrapeo incremental gitstar-ranking ({pages} paginas)...[/bold blue]")
            gs.main(max_pages=pages if pages > 0 else None)
            cur.execute("SELECT COUNT(*) FROM repos")
            after = cur.fetchone()[0]
            log_run_finish(run_id, repos_inserted=after - before, repos_filtered=0, min_stars=0, status="completed")
        conn.close()
    except Exception:
        try:
            log_run_finish(run_id, repos_inserted=0, repos_filtered=0, min_stars=0, status="failed")
        except Exception:
            pass
        conn.close()
        raise


@app.command()
def search(
    keywords: list[str] = typer.Argument(..., help="Keywords para buscar (FTS5 sobre name, description, topics)"),
    limit: int = typer.Option(20, "--limit", "-l", help="Max resultados"),
    language: str = typer.Option(None, "--language", help="Filtrar por lenguaje (ej: Python, Rust)"),
    min_stars: int = typer.Option(None, "--min-stars", help="Estrellas minimas"),
    no_update: bool = typer.Option(False, "--no-update", help="No actualizar la DB aunque este desactualizada"),
):
    """Busca repos en la base de datos usando FTS5."""
    from scraper.db_manager import search_repos_multi_keywords

    maybe_update(no_update=no_update)

    results = search_repos_multi_keywords(keywords, limit=limit * 3)

    # Filtros post-query
    if language:
        results = [r for r in results if r.get("language") and r["language"].lower() == language.lower()]
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
        desc = clean(r.get("description"), 80)
        table.add_row(r["name"], r["owner"], f"{r['stars']:,}", r["language"] or "-", desc)

    console.print(table)


@app.command()
def stats(
    no_update: bool = typer.Option(False, "--no-update", help="No actualizar la DB aunque este desactualizada"),
):
    """Muestra estadisticas de la base de datos."""
    from scraper.db_manager import get_stats

    maybe_update(no_update=no_update)

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
    min_stars: int = typer.Option(500, "--min-stars", help="Umbral minimo de estrellas"),
):
    """Ejecuta el scraper de GitHub GraphQL (barre desde Top 1 hacia abajo)."""
    from scraper.github_fetcher import fetch_top_repos

    console.print("[bold blue]Iniciando scraper GraphQL...[/bold blue]")
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
    pages: int = typer.Option(0, "--pages", "-p", help="Numero de paginas (0 = todas, max 100)"),
):
    """Scrapea gitstar-ranking.com para rankings de repos."""
    import scripts.scrape_gitstar_ranking as gs

    console.print("[bold blue]Scrapeando gitstar-ranking.com...[/bold blue]")

    gs.main(max_pages=pages if pages > 0 else None)
    console.print("[bold green]Scrapeo gitstar-ranking completado.[/bold green]")


@app.command()
def api(
    host: str = typer.Option("127.0.0.1", "--host", help="Direccion de escucha"),
    port: int = typer.Option(8000, "--port", "-p", help="Puerto"),
    dev: bool = typer.Option(False, "--dev", help="Modo desarrollo con auto-reload"),
):
    """Lanza el servidor FastAPI con la API REST."""
    import uvicorn

    console.print(f"[bold blue]Lanzando API en http://{host}:{port}[/bold blue]")
    console.print("[dim]Documentacion: http://localhost:" + str(port) + "/docs[/dim]")
    uvicorn.run("api.main:app", host=host, port=port, reload=dev)


@app.command()
def docker():
    """Levanta WheelSaver en Docker (docker compose up)."""
    import subprocess  # nosec B404 — subprocess legítimo para docker compose

    console.print("[bold blue]Levantando WheelSaver con Docker...[/bold blue]")
    result = subprocess.run(  # nosec B603/B607 — lista de args fija, sin shell, sin input del usuario
        ["docker", "compose", "up", "--build", "-d"],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )
    if result.returncode == 0:
        console.print("[bold green]WheelSaver corriendo en http://localhost:8000[/bold green]")
        console.print("[dim]Para ver logs: docker compose logs -f[/dim]")
        console.print("[dim]Para detener: docker compose down[/dim]")
    else:
        console.print("[red]Error al levantar Docker:[/red]")
        console.print(result.stderr or result.stdout)


@app.command()
def swap(
    feature: str = typer.Argument(..., help="Que estas codeando? Ej: 'pdf parser', 'auth jwt', 'http client'"),
    no_update: bool = typer.Option(False, "--no-update", help="No actualizar la DB aunque este desactualizada"),
):
    """Busca si ya existe una libreria para lo que estas codeando."""
    from scraper.db_manager import search_repos_multi_keywords

    maybe_update(no_update=no_update)

    keywords = feature.strip().split()
    console.print(f"[bold]Buscando alternativas para:[/bold] {feature}\n")

    results = search_repos_multi_keywords(keywords, limit=10)

    if not results:
        console.print("[yellow]No se encontraron librerias existentes para esto.[/yellow]")
        console.print("[dim]Puede que: 1) Sea algo muy especifico, 2) No este en la BD aun[/dim]")
        console.print("[dim]Sugerencia: prueba con keywords mas genericas[/dim]")
        raise typer.Exit()

    table = Table(title=f"Alternativas para: {feature}")
    table.add_column("Libreria", style="cyan")
    table.add_column("Estrellas", justify="right", style="bold yellow")
    table.add_column("Lenguaje")
    table.add_column("Descripcion")

    for r in results[:8]:
        desc = clean(r.get("description"), 70)
        table.add_row(f"{r['owner']}/{r['name']}", f"{r['stars']:,}", r["language"] or "-", desc)

    console.print(table)

    top = results[0]
    console.print(f"\n[bold green]Mejor opcion:[/bold green] {top['owner']}/{top['name']} ({top['stars']:,}⭐)")
    console.print(f"[dim]{top['url']}[/dim]")
    if top.get("description"):
        console.print(f"[dim]{clean(top['description'], 100)}[/dim]")
    console.print("\n[bold]Tip de instalacion:[/bold]")
    if top["language"] == "Python":
        console.print(f"  pip install {top['name']}")
    elif top["language"] in ("JavaScript", "TypeScript"):
        console.print(f"  npm install {top['name']}  # o yarn / pnpm")
    else:
        console.print(f"  Visita: {top['url']}")
    console.print(f"\n[dim]Mas resultados con: python cli.py search {' '.join(keywords)} --limit 20[/dim]")


# Comandos extraídos (definidos en cli_commands/*)
app.command()(ready)
app.command(name="audit-code")(audit_code)
app.command()(skillify)
app.command()(ask)


if __name__ == "__main__":
    # Shell completion (Typer nativo):
    #   python cli.py --install-completion  → instala autocompletado
    #   python cli.py --show-completion     → muestra script de completion
    app()
