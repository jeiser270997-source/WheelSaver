# Contexto de WheelSaver

WheelSaver es un scraper de GitHub y una herramienta de auditoría por IA.
Su objetivo es mantener una base de datos local (`data/top_repos.db`) con
los repositorios de GitHub de más de 500 estrellas, usando SQLite y FTS5
para búsquedas ultrarrápidas.

## Comandos Principales
- Ejecutar scraper: `python scraper/github_fetcher.py`
- Buscar manual: `python .agents/skills/wheel_saver/scripts/search_db.py <keyword>`

## Arquitectura
- `scraper/github_fetcher.py`: Lógica de paginación GraphQL, filtros de calidad y rate-limiting.
- `scraper/db_manager.py`: ORM ligero, upserts y reconstrucción del índice FTS5.
- `.agents/skills/wheel_saver/`: Skill de IA para que Claude audite proyectos y recomiende librerías.
- `data/top_repos.db`: Base de datos SQLite (~14k repos, índice FTS5).
- `scripts/import_from_evanli.py`: Importa Top 100 por lenguaje desde EvanLi/Github-Ranking.
- `scripts/scrape_gitstar_ranking.py`: Scrapea gitstar-ranking.com (~5k repos, 100 páginas).

## Comandos Auxiliares
- Importar desde EvanLi: `python scripts/import_from_evanli.py`
- Scrapear gitstar-ranking: `python scripts/scrape_gitstar_ranking.py [--pages N]`
- Scrapeo completo (100 págs, ~2.5 min): `python scripts/scrape_gitstar_ranking.py`

## Reglas de Desarrollo
- No usar ORMs pesados (SQLAlchemy), mantener SQLite nativo.
- Siempre manejar los rate-limits de la API de GitHub.
- Si se modifica el esquema de la BD, proveer un script de migración.
- El scraper siempre barre desde el Top 1 hacia abajo para refrescar datos.
- Las fuentes externas (EvanLi, gitstar) no aportan `github_id`; se usa un hash SHA-256 de `owner/name`.
- `upsert_external_repos()` en db_manager maneja IDs sintéticos automáticamente.
