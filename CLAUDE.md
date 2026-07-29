# Contexto de WheelSaver

WheelSaver es un scraper de GitHub y una herramienta de auditoria por IA / local.
Su objetivo es mantener una base de datos local (`~/.wheelsaver/top_repos.db`) con
los repositorios de GitHub de mas de 500 estrellas, usando SQLite y FTS5
para busquedas ultrarrápidas y offline.

## Comandos Principales

### CLI Global (instalado via `pip install -e .`)
- Buscar repos:  `wheelsaver search <keywords> [--limit N] [--language L] [--min-stars N]`
- Estadisticas:  `wheelsaver stats`
- Scraper:       `wheelsaver scrape [--min-stars 500]`
- Import EvanLi: `wheelsaver import evanli`
- Import Gitstar: `wheelsaver import gitstar [--pages N]`
- API REST:      `wheelsaver api [--port 8000]`
- Checklist:     `wheelsaver ready [--path .]`
- Auditoria:     `wheelsaver audit-code <ruta>`
- Alternativas:  `wheelsaver swap <feature>`

### Tests
- `python -m pytest -v` (80+ tests unitarios, de API, CLI e interfaz Playwright E2E)

## Arquitectura
- `api/llm.py`: Sistema RAG multi-LLM con failover automático entre proveedores free tier, timeout global de 45s, caché de respuestas y modo offline.
- `scraper/db_manager.py`: ORM ligero, upserts, FTS5 con triggers incrementales, `make_repo_id()`, `SYNONYM_MAP` para expansión de sinónimos técnicos.
- `cli.py`: Punto de entrada unificado con Typer + Rich (`wheelsaver api --dev`, host local por defecto `127.0.0.1`).
- `api/main.py`: API REST con FastAPI (endpoints: `/search`, `/stats`, `/repos`, `/languages`, `/top`, `/health`, `/scrape`, `/ask`) protegida con rate limiting y guardias en `/scrape`.
- `services/project_auditor.py`: Detector modular de stack del proyecto.
- `services/static_analyzer.py`: Análisis estático (bandit + vulture + radon).
- `~/.wheelsaver/top_repos.db`: Base de datos SQLite (25,411 repos, indice FTS5).
- `tests/`: 80+ tests con pytest + BD in-memory + Playwright E2E + GitHub Actions CI (`.github/workflows/test.yml`).

## Reglas de Desarrollo
- Ejecución 100% local y autónoma (sin dependencias de GitHub Actions ni CI externos).
- No usar ORMs pesados (SQLAlchemy), mantener SQLite nativo con WAL + FTS5.
- Siempre manejar los rate-limits de la API de GitHub y fallback offline.
- Si se modifica el esquema de la BD, proveer un script de migracion.
- Las fuentes externas (EvanLi, gitstar) no aportan `github_id`; se usa hash SHA-256 de `owner/name`.
- `upsert_external_repos()` en db_manager maneja IDs sinteticos automaticamente.
- httpx es el cliente HTTP preferido sobre requests.

