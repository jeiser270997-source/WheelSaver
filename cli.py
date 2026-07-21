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
"""

import os
import re
import sys

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Reconfigurar stdout/stderr en Windows para evitar UnicodeEncodeError con cp1252
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

app = typer.Typer(
    name="wheelsaver",
    help="WheelSaver — GitHub repo scraper, search & audit tool",
    no_args_is_help=True,
)
import_group = typer.Typer(help="Import data from external sources")
app.add_typer(import_group, name="import")

console = Console()


# Sanitizador para Windows cp1252 — limpia emojis y no-ASCII
def clean(text, max_len=80):
    """Limpia texto para terminal Windows."""
    if not text:
        return ""
    # Remueve todo lo que no sea ASCII imprimible (+ acentos comunes)
    cleaned = re.sub(r"[^\x20-\x7EÀ-ÿĀ-ſ]", "", text)
    return cleaned[:max_len] + "..." if len(text) > max_len else cleaned


@app.command()
def search(
    keywords: list[str] = typer.Argument(
        ..., help="Keywords para buscar (FTS5 sobre name, description, topics)"
    ),
    limit: int = typer.Option(20, "--limit", "-l", help="Max resultados"),
    language: str = typer.Option(
        None, "--language", help="Filtrar por lenguaje (ej: Python, Rust)"
    ),
    min_stars: int = typer.Option(None, "--min-stars", help="Estrellas minimas"),
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
        desc = clean(r.get("description"), 80)
        table.add_row(r["name"], r["owner"], f"{r['stars']:,}", r["language"] or "-", desc)

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
    import sys

    import scripts.scrape_gitstar_ranking as gs

    console.print("[bold blue]Scrapeando gitstar-ranking.com...[/bold blue]")

    # Guardar args originales y poner los nuestros
    old_argv = sys.argv
    args = (
        ["scrape_gitstar_ranking.py", f"--pages={pages}"]
        if pages
        else ["scrape_gitstar_ranking.py"]
    )
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


@app.command()
def docker():
    """Levanta WheelSaver en Docker (docker compose up)."""
    import subprocess
    import sys

    console.print("[bold blue]Levantando WheelSaver con Docker...[/bold blue]")
    result = subprocess.run(
        [sys.executable, "-m", "docker", "compose", "up", "--build", "-d"],
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
def ready(
    path: str = typer.Option(".", "--path", help="Ruta del proyecto a analizar"),
):
    """Escanea un proyecto y genera checklist de lo que le falta."""
    from pathlib import Path

    target = Path(path).resolve()
    console.print(f"[bold]Analizando proyecto:[/bold] {target}")
    console.print()

    # Detectar stack usando la capa de servicio
    import sys

    sys.path.append(str(Path(__file__).parent))
    from services.project_auditor import detect_stack_and_framework

    audit_data = detect_stack_and_framework(target)

    console.print(
        Panel(
            f"[bold]Stack:[/bold] {audit_data['stack_str']}\n"
            f"[bold]Framework:[/bold] {audit_data['framework'] or 'No detectado'}\n"
            f"[bold]Ruta:[/bold] {target}",
            title="Proyecto Detectado",
            border_style="blue",
        )
    )

    # Checklist
    checks = audit_data["checks"]

    table = Table(title="Checklist del Proyecto")
    table.add_column("Estado", justify="center")
    table.add_column("Categoria", style="bold")
    table.add_column("Recomendacion")

    missing_categories = []

    for label, ok, cat, keywords in checks:
        if ok:
            table.add_row("✅", label, "[dim]Listo[/dim]")
        else:
            table.add_row("❌", label, f"[yellow]Buscar:[/yellow] {keywords}")
            missing_categories.append((label, cat, keywords))

    console.print(table)

    # Si falta algo, buscar en BD
    if missing_categories:
        console.print("\n[bold yellow]Buscando recomendaciones en la BD...[/bold yellow]\n")
        for label, cat, keywords in missing_categories[:3]:  # Max 3 busquedas
            kw_list = keywords.split()[:3]
            kw_str = " ".join(kw_list)
            from scraper.db_manager import search_repos_multi_keywords

            results = search_repos_multi_keywords(kw_list, limit=3)
            if results:
                rec_table = Table(title=f"Recomendaciones para {label}")
                rec_table.add_column("Repo")
                rec_table.add_column("Estrellas", justify="right")
                rec_table.add_column("Descripcion")
                for r in results:
                    desc = clean(r.get("description"), 60)
                    rec_table.add_row(r["name"], f"{r['stars']:,}", desc)
                console.print(rec_table)
            else:
                console.print(f"[dim]{label}: No se encontraron recomendaciones en la BD[/dim]")

    console.print("\n[bold blue]🤖 Ejecutando Auditoría Profunda con IA...[/bold blue]")
    import asyncio
    from api.llm import audit_project_with_ai

    with console.status("[bold green]Analizando arquitectura + código estático...[/bold green]"):
        report = asyncio.run(
            audit_project_with_ai(
                audit_data,
                missing_categories,
                static_analysis=audit_data.get("static_analysis"),
            )
        )
        
    console.print(Panel(report, title="[bold magenta]WheelSaver Deep Audit[/bold magenta]", border_style="cyan"))
    
    if missing_categories:
        console.print("\n[dim]TIP: Corre 'python cli.py search <keyword>' para explorar mas librerias que cubran estos huecos.[/dim]")


@app.command()
def swap(
    feature: str = typer.Argument(
        ..., help="Que estas codeando? Ej: 'pdf parser', 'auth jwt', 'http client'"
    ),
):
    """Busca si ya existe una libreria para lo que estas codeando."""
    from scraper.db_manager import search_repos_multi_keywords

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
    console.print(
        f"\n[bold green]Mejor opcion:[/bold green] {top['owner']}/{top['name']} ({top['stars']:,}⭐)"
    )
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
    console.print(
        f"\n[dim]Mas resultados con: python cli.py search {' '.join(keywords)} --limit 20[/dim]"
    )


@app.command(name="audit-code")
def audit_code(
    path: str = typer.Argument(
        ".", help="Ruta al proyecto Python a analizar (por defecto: directorio actual)"
    ),
):
    """Analiza seguridad, codigo muerto y complejidad (bandit + vulture + radon)."""
    from pathlib import Path

    from services.static_analyzer import analyze_python_project

    target = Path(path).resolve()
    if not target.exists():
        console.print(f"[bold red]Error: la ruta no existe: {target}[/bold red]")
        raise typer.Exit(1)

    console.print(f"[bold blue]Analizando codigo en:[/bold blue] {target}\n")

    with console.status("[bold green]Ejecutando bandit, vulture y radon...[/bold green]"):
        report = analyze_python_project(target)

    # Seguridad (bandit)
    security = report.get("security", {})
    if not security.get("available"):
        console.print(
            f"[yellow]Seguridad (bandit): no disponible — "
            f"{security.get('error', 'desconocido')}[/yellow]"
        )
    else:
        sev = security.get("by_severity", {})
        panel = Panel(
            f"[bold]Total hallazgos:[/bold] {security.get('total_findings', 0)}\n"
            f"[red]HIGH:[/red] {sev.get('HIGH', 0)}  "
            f"[yellow]MEDIUM:[/yellow] {sev.get('MEDIUM', 0)}  "
            f"[dim]LOW:[/dim] {sev.get('LOW', 0)}",
            title="Seguridad (bandit)",
            border_style="red",
        )
        console.print(panel)

        findings = security.get("top_findings", [])
        if findings:
            table = Table(title="Top hallazgos de seguridad")
            table.add_column("Archivo", style="cyan")
            table.add_column("Linea", justify="right")
            table.add_column("Severidad")
            table.add_column("Problema")
            for f in findings:
                table.add_row(
                    clean(f.get("file", ""), 40),
                    str(f.get("line", "")),
                    f.get("severity", ""),
                    clean(f.get("issue", ""), 70),
                )
            console.print(table)

    # Codigo muerto (vulture)
    dead_code = report.get("dead_code", {})
    if not dead_code.get("available"):
        console.print(
            f"[yellow]Codigo muerto (vulture): no disponible — "
            f"{dead_code.get('error', 'desconocido')}[/yellow]"
        )
    else:
        console.print(
            f"\n[bold]Codigo muerto (vulture):[/bold] "
            f"{dead_code.get('total_findings', 0)} hallazgos"
        )
        for line in dead_code.get("top_findings", []):
            console.print(f"  [dim]{clean(line, 100)}[/dim]")

    # Complejidad (radon)
    complexity = report.get("complexity", {})
    if not complexity.get("available"):
        console.print(
            f"[yellow]Complejidad (radon): no disponible — "
            f"{complexity.get('error', 'desconocido')}[/yellow]"
        )
    else:
        console.print(
            f"\n[bold]Alta complejidad (radon):[/bold] "
            f"{complexity.get('high_complexity_count', 0)} funciones con rango D/E/F"
        )
        findings = complexity.get("top_findings", [])
        if findings:
            table = Table(title="Funciones mas complejas")
            table.add_column("Archivo", style="cyan")
            table.add_column("Funcion")
            table.add_column("Complejidad", justify="right")
            table.add_column("Rango")
            for f in findings:
                table.add_row(
                    clean(f.get("file", ""), 40),
                    clean(f.get("name", ""), 30),
                    str(f.get("complexity", "")),
                    f.get("rank", ""),
                )
            console.print(table)


@app.command()
def skillify(
    repo: str = typer.Argument(
        ..., help="Repositorio a convertir en skill. Ej: 'tiangolo/fastapi'"
    ),
):
    """Convierte un repositorio en una Skill de IA local."""
    import asyncio
    import httpx
    import os
    from api.llm import generate_skill_from_repo
    
    console.print(f"[bold blue]🪄 Iniciando Meta-Skill: wheel-skillify para {repo}...[/bold blue]")
    
    # 1. Fetch repo info
    headers = {}
    gh_token = os.getenv("GITHUB_TOKEN")
    if gh_token:
        headers["Authorization"] = f"token {gh_token}"
        
    with console.status("[bold green]Descargando datos del repositorio desde GitHub...[/bold green]"):
        try:
            r_info = httpx.get(f"https://api.github.com/repos/{repo}", headers=headers, timeout=10, follow_redirects=True)
            if r_info.status_code == 401:
                # Token invalido, intentar sin auth
                r_info = httpx.get(f"https://api.github.com/repos/{repo}", timeout=10, follow_redirects=True)
            r_info.raise_for_status()
            repo_data = r_info.json()
            description = repo_data.get("description", "")
            default_branch = repo_data.get("default_branch", "main")
            
            # Fetch readme
            r_readme = httpx.get(f"https://raw.githubusercontent.com/{repo}/{default_branch}/README.md", timeout=10, follow_redirects=True)
            readme = r_readme.text if r_readme.status_code == 200 else ""
        except Exception as e:
            console.print(f"[bold red]Error al contactar GitHub: {e}[/bold red]")
            raise typer.Exit(1)
            
    # 2. Generar SKILL.md usando IA
    with console.status("[bold green]Generando SKILL.md con IA (RAG)...[/bold green]"):
        skill_content = asyncio.run(generate_skill_from_repo(repo, description, readme))
        
    # 3. Guardar en ~/.gemini/config/skills/[repo_name]/SKILL.md
    repo_name = repo.split("/")[-1].lower()
    skills_dir = os.path.expanduser("~/.gemini/config/skills")
    target_dir = os.path.join(skills_dir, repo_name)
    os.makedirs(target_dir, exist_ok=True)
    
    skill_path = os.path.join(target_dir, "SKILL.md")
    with open(skill_path, "w", encoding="utf-8") as f:
        f.write(skill_content)
        
    console.print(Panel(
        f"✅ Skill generada exitosamente en:\n[dim]{skill_path}[/dim]\n\n"
        f"Tu IA ahora tiene preinstalado el conocimiento para usar [bold]{repo}[/bold].",
        title="Wheel-Skillify", border_style="green"
    ))
import asyncio


@app.command()
def ask(
    question: str = typer.Argument(
        ...,
        help="Tu pregunta para la IA. Ej: 'Cual es el mejor framework de python para graficos?'",
    ),
    provider: str = typer.Option(
        None,
        "--provider",
        "-p",
        help="Proveedor especifico (groq, cerebras, google, mistral, etc.)",
    ),
):
    """Consulta a la IA (multi-proveedor) usando la base de datos local como contexto (RAG). Usa failover automático entre proveedores free tier."""
    console.print(f"[bold blue]Consultando a la IA sobre:[/bold blue] {question}")

    from api.llm import expand_search_query
    from scraper.db_manager import search_repos_multi_keywords, search_repos

    # Extraer keywords con LLM
    keywords = asyncio.run(expand_search_query(question))
    
    if not keywords:
        repos = []
    elif len(keywords) == 1:
        repos = search_repos(keywords[0], limit=10)
    else:
        repos = search_repos_multi_keywords(keywords, limit=10)

    if repos:
        console.print(f"[dim]Contexto encontrado: {len(repos)} repositorios.[/dim]")
    else:
        console.print("[dim]Contexto encontrado: 0 repositorios.[/dim]")

    from api.llm import ask_llm_about_repos

    with console.status("[bold green]Generando respuesta de la IA...[/bold green]"):
        answer = asyncio.run(ask_llm_about_repos(question, repos))

    console.print(
        Panel(answer, title="[bold magenta]WheelSaver AI[/bold magenta]", border_style="cyan")
    )


if __name__ == "__main__":
    # Shell completion (Typer nativo):
    #   python cli.py --install-completion  → instala autocompletado
    #   python cli.py --show-completion     → muestra script de completion
    app()
