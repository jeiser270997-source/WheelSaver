# Contexto de WheelSaver

WheelSaver es un scraper de GitHub y una herramienta de auditoria por IA.
Su objetivo es mantener una base de datos local (`data/top_repos.db`) con
los repositorios de GitHub de mas de 500 estrellas, usando SQLite y FTS5
para busquedas ultrarrápidas.

## Comandos Principales

### CLI Unificado (Typer + Rich)
- Buscar repos:  `python cli.py search <keywords> [--limit N] [--language L] [--min-stars N]`
- Estadisticas:  `python cli.py stats`
- Scraper:       `python cli.py scrape [--min-stars 500]`
- Import EvanLi: `python cli.py import evanli`
- Import Gitstar: `python cli.py import gitstar [--pages N]`
- API REST:      `python cli.py api [--port 8000]`

### Scripts Legacy (siguen funcionando)
- `python scraper/github_fetcher.py --min-stars 500`
- `python scripts/import_from_evanli.py`
- `python scripts/scrape_gitstar_ranking.py --pages 10`
- `python .agents/skills/wheel_saver/scripts/search_db.py <keyword>`

### Tests
- `python -m pytest tests/ -v`

## Arquitectura
- `api/llm.py`: Sistema multi-LLM con failover automático entre proveedores free tier (Groq, Cerebras, OpenRouter, NVIDIA, SambaNova, Mistral, HuggingFace, Google Gemini, Cohere). Usa `AsyncOpenAI` para APIs compatibles y `httpx` para las nativas.
- `scraper/db_manager.py`: ORM ligero, upserts, FTS5, `make_repo_id()` para fuentes externas.
- `cli.py`: Punto de entrada unificado con Typer + Rich (tablas, paneles, colores).
- `api/main.py`: API REST con FastAPI (endpoints: /search, /stats, /repos, /languages, /top, /health).
- `scripts/import_from_evanli.py`: Importa Top 100 por lenguaje (httpx + tqdm).
- `scripts/scrape_gitstar_ranking.py`: Scrapea gitstar-ranking.com (httpx + tqdm).
- `.agents/skills/wheel_saver/`: Skill de IA para que Claude audite proyectos.
- `data/top_repos.db`: Base de datos SQLite (~23k repos, indice FTS5).
- `tests/`: Tests con pytest + BD in-memory (18 tests).

## Reglas de Desarrollo
- No usar ORMs pesados (SQLAlchemy), mantener SQLite nativo.
- Siempre manejar los rate-limits de la API de GitHub.
- Si se modifica el esquema de la BD, proveer un script de migracion.
- El scraper siempre barre desde el Top 1 hacia abajo para refrescar datos.
- Las fuentes externas (EvanLi, gitstar) no aportan `github_id`; se usa hash SHA-256 de `owner/name`.
- `upsert_external_repos()` en db_manager maneja IDs sinteticos automaticamente.
- httpx es el cliente HTTP preferido sobre requests.
