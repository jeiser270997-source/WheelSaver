# WheelSaver Audit — WheelSaver (v3.3.2 self-audit actual)
> Auditado el 2026-08-12 | ~25k repos en la base de datos

## Estado actual (Deep Loop Audit v3.3.2)

### ✅ Verde — Verificado con herramientas del propio proyecto
- **Tests**: 81/81 pasan (`pytest -v`).
- **Seguridad (bandit)**: 0 hallazgos.
- **Lint (ruff)**: all checks passed.
- **Complejidad (radon)**: 0 funciones rango D/E/F · todos los módulos con índice de mantenibilidad grado A.
- **Secretos**: 0 leaks detectados · `.env` NO está trackeado en git.
- **CI**: `.github/workflows/test.yml` ejecuta `pytest` en cada Push/PR (Python 3.12).

### 🔴 Seguridad (resuelto en v3.3.2)
- **XSS almacenado en frontend**: se reemplazó `innerHTML` por DOM API (`textContent` + `createElement`) en `frontend/app.js`, con validación de URLs (`safeExternalUrl` solo permite http/https) y `rel="noopener noreferrer"`.
- **API key de Google en URL**: `_ask_google` ahora envía la key en el header `x-goog-api-key` (nunca en query string) — `api/llm_providers.py`.
- **Comparación de `X-API-Key`**: `hmac.compare_digest` en tiempo constante — `api/main.py`.
- **CORS `*`**: restringido por defecto a `http://127.0.0.1:8000,http://localhost:8000`, ampliable con `ALLOWED_ORIGINS`.

### 🟡 Deuda técnica (resuelto en v3.3.2)
- `repomix_last_run.log` fuera de git (`git rm --cached` + `.gitignore`).
- Código muerto eliminado: `REPOS_PER_PAGE` (scrape_gitstar_ranking) y `make_table` (cli_ui).
- Imports movidos al top de `api/main.py` (`os`, `datetime`, `pydantic.BaseModel`).
- `StaticFiles` del frontend resuelto contra `__file__` (independiente del cwd).
- `requirements.txt` con versiones fijadas (`==`) para reproducibilidad.
- `Dockerfile` con usuario no-root (`wheelsaver`) y build toolchain purgado; volumen de `docker-compose` alineado a `/home/wheelsaver/.wheelsaver`.

## Historial (v3.3)
- ✅ **Arquitectura Limpia y Base de Datos Asíncrona:** `aiosqlite`, lógica en `api/repository.py`, dependencias limpias en `api/main.py`.
- ✅ **Cobertura de Código:** `pytest-asyncio` con cobertura en la API.
- ✅ **CI/CD:** Pipeline de tests en GitHub Actions (resuelto tras el informe v3.3).
- ✅ **Git LFS**: Configurado para `top_repos.db` para no inflar el repositorio con binarios.
- ✅ **Seguridad**: `.env.example` con recomendación de tokens Read-Only.

## Decisiones de diseño (descartadas a propósito — proyecto personal)
- **Servidor de Producción**: uvicorn con 1 worker es suficiente (no es SaaS).
- **Caché**: SQLite local WAL es ultrarrápido para uso personal.
- **Background Task Worker**: sin brokers complejos; `asyncio.to_thread` basta.

## Pasada 2026-08-15 (deep loop audit a nivel producción)
- **Tests: 80/80 PASS** (`python -m pytest tests/ -q`).
- **DB real: 20,073 repos** (no 25,411) — README/CLAUDE actualizados a v3.3.2.
- **Diff previo (v3.3.2) guardado**: refactor search/synonyms/scoring extraídos de
  db_manager, api/llm.py slim (−300 líneas), frontend XSS fix, Docker no-root,
  requirements fijados — quedaba sin commitear; incluido en el checkpoint.
- **Eliminados**: `CREAR REPOMIX.BAT`, `GENERARREPOMIX.BAT`, `test_ui.py` (raíz,
  duplicado de tests/test_e2e_ui.py), `repomix_*.md` + `repomix_parts/` +
  `wheelsaver.egg-info` + `data/typesense/` (artefactos gitignored, FS limpio).
- **Integración ecosistema verificada**: Faceless lee la DB real vía
  `services/wheel_*.js` (better-sqlite3 + FTS5) — no ports estáticos.
- **Pendiente (no deuda)**: `scripts/deduplicate_db.py` es utilidad manual de
  mantenimiento (rebuild FTS) — se conserva.
