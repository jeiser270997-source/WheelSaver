# WheelSaver Audit — WheelSaver (autoauditoria)
> Auditado el 2026-07-07 | 22,787 repos analizados en la base de datos

## Lo que entendi de WheelSaver

WheelSaver es un scraper de GitHub + auditor por IA que mantiene una base de datos
SQLite local con ~23k repositorios top. Actualmente tiene:

- **Stack**: Python puro, SQLite3/FTS5, requests, dotenv
- **3 fuentes de datos**: GraphQL API, EvanLi/Github-Ranking, gitstar-ranking.com
- **Skill de IA**: Claude audita proyectos y recomienda librerias
- **CI/CD**: GitHub Actions semanal con los 3 importadores
- **CLI basico**: Scripts sueltos (github_fetcher.py, search_db.py)

**Lo que le falta** para ser una herramienta verdaderamente profesional:
- Una interfaz web o API para consultar la BD sin necesidad de Python
- Un CLI unificado y bonito (hoy son scripts sueltos)
- Tests automatizados
- Exportacion de datos (CSV, JSON)
- Dashboard de estadisticas y graficos

---

## Resumen de la Busqueda

- Keywords analizadas: `fastapi`, `typer`, `rich`, `textual`, `pytest`, `httpx`,
  `tqdm`, `alembic`, `sqlite-utils`, `gunicorn`, `uvicorn`, `celery`
- Repos encontrados: 300+
- Recomendaciones finales: 8

---

## Recomendaciones

### 1. FastAPI — 100,209 ⭐
**URL**: https://github.com/fastapi/fastapi
**Por que te sirve**: WheelSaver necesita una API REST para que cualquier herramienta
(Claude, web, CLI) pueda consultar la BD sin tener que ejecutar Python localmente.
FastAPI es el framework web Python mas popular, con validacion automatica
(Pydantic), documentacion Swagger automatica, y rendimiento excelente.
**Como integrarlo**:
```python
# api/main.py
from fastapi import FastAPI
from scraper.db_manager import search_repos, get_stats

app = FastAPI(title="WheelSaver API")

@app.get("/search")
def search(q: str, limit: int = 10):
    return search_repos(q, limit)

@app.get("/stats")
def stats():
    return get_stats()
```
```bash
pip install fastapi uvicorn
uvicorn api.main:app --reload
# → http://localhost:8000/docs (Swagger UI automatico)
```
**Tags**: `api`, `python`, `web-framework`, `rest`

---

### 2. Typer — 19,710 ⭐
**URL**: https://github.com/fastapi/typer
**Por que te sirve**: Hoy WheelSaver tiene scripts sueltos con argparse.
Typer (del mismo autor de FastAPI) te permite crear un CLI unificado con solo
anotaciones de tipo. Auto-genera --help, autocompletado, y colores.
**Como integrarlo**:
```python
# cli.py
import typer
app = typer.Typer()

@app.command()
def search(keyword: str, limit: int = 10):
    """Busca repos por keyword en la base de datos."""
    ...

@app.command()
def stats():
    """Muestra estadisticas de la BD."""
    ...

@app.command()
def scrape(min_stars: int = 500):
    """Ejecuta el scraper de GitHub."""
    ...

if __name__ == "__main__":
    app()
```
```bash
pip install typer
python cli.py search fastapi --limit 5
python cli.py --help
```
**Tags**: `cli`, `python`, `fastapi`

---

### 3. Rich — 56,813 ⭐
**URL**: https://github.com/Textualize/rich
**Por que te sirve**: Las salidas actuales de los scripts son texto plano y
emojis. Rich te da tablas formateadas, barras de progreso animadas, resaltado
de sintaxis, y markdown renderizado en terminal.
**Como integrarlo**:
```python
from rich.console import Console
from rich.table import Table
from rich.progress import track

console = Console()

def show_results(repos):
    table = Table(title="Repos encontrados")
    table.add_column("Nombre", style="cyan")
    table.add_column("Estrellas", style="green")
    table.add_column("Lenguaje", style="yellow")
    for r in repos:
        table.add_row(r['name'], str(r['stars']), r['language'])
    console.print(table)
```
**Tags**: `cli`, `terminal`, `python`, `ui`

---

### 4. Textual — 36,515 ⭐
**URL**: https://github.com/Textualize/textual
**Por que te sirve**: Si quieres llevar WheelSaver al siguiente nivel, Textual
te permite construir una interfaz de terminal interactiva (TUI) para navegar
la BD sin tener que escribir comandos. Como un "explorador de repos" en la
terminal.
**Tags**: `tui`, `terminal`, `python`, `ui`

---

### 5. pytest — 13,660 ⭐
**URL**: https://github.com/pytest-dev/pytest
**Por que te sirve**: WheelSaver tiene CERO tests. Para una herramienta que
procesa datos y recomienda librerias, tener tests es critico. pytest es el
framework de testing mas usado en Python.
**Como integrarlo**:
```bash
pip install pytest
# Crear tests/test_scraper.py
pytest -v
```
**Tags**: `testing`, `python`, `quality`

---

### 6. httpx — 15,341 ⭐
**URL**: https://github.com/encode/httpx
**Por que te sirve**: WheelSaver usa `requests` para las llamadas HTTP. httpx
es su sucesor moderno: soporta async, HTTP/2, timeouts nativos, y una API
mas limpia. Ideal para el scraper y los importadores.
**Tags**: `http`, `python`, `async`, `client`

---

### 7. alembic — 4,229 ⭐
**URL**: https://github.com/sqlalchemy/alembic
**Por que te sirve**: El esquema de la BD ha cambiado varias veces
(is_archived, run_history, etc.) y cada vez toca hacer migraciones a mano.
Alembic (de SQLAlchemy) gestiona migraciones de esquema automaticamente.
**Tags**: `database`, `migration`, `python`

---

### 8. tqdm — 31,229 ⭐
**URL**: https://github.com/tqdm/tqdm
**Por que te sirve**: El scraper actual imprime lineas de texto para el
progreso. tqdm te da barras de progreso automaticas y elegantes para
los bucles de importacion.
```python
from tqdm import tqdm
for repo in tqdm(repos, desc="Importando"):
    upsert_repos([repo])
```
**Tags**: `cli`, `progress`, `python`

---

## Acciones Recomendadas

1.  **Crear CLI unificado con Typer + Rich** — Reemplazar los 3 scripts
    sueltos por un solo comando `wheelsaver search|scrape|stats|import`
    con salida formateada en tablas.
2.  **Montar API con FastAPI + uvicorn** — Para que Claude y otras
    herramientas consulten la BD via HTTP.
3.  **Agregar tests con pytest** — Minimum: test_upsert.py, test_search.py,
    test_scraper.py. Sin tests no hay produccion confiable.
4.  **Reemplazar requests por httpx** — En el scraper y los importadores.
    Mejor manejo de timeouts y errores.
5.  **Agregar barras de progreso con tqdm** — En los bucles de importacion
    de EvanLi y gitstar-ranking.
6.  **Migraciones con alembic** — Para cuando el esquema cambie de nuevo.
