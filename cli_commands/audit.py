"""cli_commands/audit.py — Comandos de auditoría (ready, audit-code)."""

import asyncio
from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table

from cli_ui import clean, console


def ready(
    path: str = typer.Option(".", "--path", help="Ruta del proyecto a analizar"),
):
    """Escanea un proyecto y genera checklist de lo que le falta."""
    from api.llm import audit_project_with_ai
    from scraper.db_manager import search_repos_multi_keywords
    from services.project_auditor import detect_stack_and_framework

    target = Path(path).resolve()
    console.print(f"[bold]Analizando proyecto:[/bold] {target}")
    console.print()

    # Detectar stack usando la capa de servicio
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
        if len(missing_categories) > 3:
            console.print(f"[dim]Mostrando recomendaciones solo para las primeras 3 de {len(missing_categories)} categorias faltantes.[/dim]")
        for label, cat, keywords in missing_categories[:3]:  # Max 3 busquedas
            kw_list = keywords.split()[:3]
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


def audit_code(
    path: str = typer.Argument(".", help="Ruta al proyecto Python a analizar (por defecto: directorio actual)"),
):
    """Analiza seguridad, codigo muerto y complejidad (bandit + vulture + radon)."""
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
        console.print(f"[yellow]Seguridad (bandit): no disponible — {security.get('error', 'desconocido')}[/yellow]")
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
        console.print(f"[yellow]Codigo muerto (vulture): no disponible — {dead_code.get('error', 'desconocido')}[/yellow]")
    else:
        console.print(f"\n[bold]Codigo muerto (vulture):[/bold] {dead_code.get('total_findings', 0)} hallazgos")
        for line in dead_code.get("top_findings", []):
            console.print(f"  [dim]{clean(line, 100)}[/dim]")

    # Complejidad (radon)
    complexity = report.get("complexity", {})
    if not complexity.get("available"):
        console.print(f"[yellow]Complejidad (radon): no disponible — {complexity.get('error', 'desconocido')}[/yellow]")
    else:
        console.print(f"\n[bold]Alta complejidad (radon):[/bold] {complexity.get('high_complexity_count', 0)} funciones con rango D/E/F")
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

    # Escaneo de Secretos y Leaks
    secrets = report.get("secrets", {})
    if secrets.get("total_findings", 0) > 0:
        sec_table = Table(title="🔐 Secretos / Leaks Detectados", border_style="red")
        sec_table.add_column("Archivo", style="cyan")
        sec_table.add_column("Linea", justify="right")
        sec_table.add_column("Problema", style="bold red")
        for f in secrets.get("top_findings", []):
            sec_table.add_row(clean(f.get("file", ""), 40), str(f.get("line", "")), f.get("issue", ""))
        console.print(sec_table)
    else:
        console.print("\n[bold green]🔐 Escaneo de Secretos: 0 leaks detectados en codigo fuente.[/bold green]")

    # Deuda Técnica & Violaciones SRP (>300 líneas)
    smells = report.get("code_smells", {})
    if smells.get("large_files_count", 0) > 0:
        smell_table = Table(title="⚠️ Deuda Tecnica: Archivos >300 Líneas (Regla SRP)", border_style="yellow")
        smell_table.add_column("Archivo", style="cyan")
        smell_table.add_column("Líneas", justify="right", style="bold yellow")
        smell_table.add_column("Recomendación")
        for f in smells.get("top_large_files", []):
            smell_table.add_row(clean(f.get("file", ""), 50), f"{f.get('lines', 0):,}", f.get("issue", ""))
        console.print(smell_table)
