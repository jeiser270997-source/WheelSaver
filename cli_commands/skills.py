"""cli_commands/skills.py — Comandos basados en IA (skillify, ask)."""

import asyncio
import os

import httpx
import typer
from rich.panel import Panel

from cli_ui import console


def skillify(
    repo: str = typer.Argument(..., help="Repositorio a convertir en skill. Ej: 'tiangolo/fastapi'"),
):
    """Convierte un repositorio en una Skill de IA local."""
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

    console.print(
        Panel(
            f"✅ Skill generada exitosamente en:\n[dim]{skill_path}[/dim]\n\n"
            f"Tu IA ahora tiene preinstalado el conocimiento para usar [bold]{repo}[/bold].",
            title="Wheel-Skillify",
            border_style="green",
        )
    )


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

    from api.llm import ask_llm_about_repos, expand_search_query
    from scraper.db_manager import search_repos, search_repos_multi_keywords

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

    with console.status("[bold green]Generando respuesta de la IA...[/bold green]"):
        answer = asyncio.run(ask_llm_about_repos(question, repos))

    console.print(Panel(answer, title="[bold magenta]WheelSaver AI[/bold magenta]", border_style="cyan"))
