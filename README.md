# 🛞 WheelSaver

**Tu biblioteca offline de GitHub + 3 skills de IA para no reinventar la rueda.**

WheelSaver descarga automaticamente los mejores repositorios de GitHub (>500⭐)
y los almacena en una base de datos SQLite local con busqueda FTS5 ultrarrápida.
Incluye skills nativos para Claude Code que auditan tus proyectos y te recomiendan
librerias existentes, evitando que codees desde cero lo que ya esta resuelto.

```
📦 25,411 repos · 🌐 149 lenguajes · ⚡ Búsqueda FTS5 en milisegundos · 🛡️ v3.3.1 (commit dfa9bca)
```

## Componentes

| Componente | Qué hace |
|---|---|
| **3 Scrapers** | GitHub GraphQL API + EvanLi/Github-Ranking + gitstar-ranking.com |
| **Base de datos** | SQLite + FTS5 con triggers incrementales |
| **CLI unificado** | 12 comandos con Typer + Rich (`wheelsaver api --dev`, etc.) |
| **API REST** | FastAPI con 9+ endpoints + Swagger en `/docs` |
| **Seguridad** | Sanitización anti-SQL/FTS injection, Rate Limiting (20 req/min search, 5 req/min ask), protección `/scrape` vía `SCRAPE_ENABLED`/`X-API-Key` |
| **3 Skills IA** | `wheel_saver` `wheel-ready` `wheel-swap` para Claude Code / Gemini / Antigravity |
| **Análisis estático** | `wheelsaver audit-code` ejecuta bandit + vulture + radon |
| **CI & Tests** | GitHub Actions CI + 80+ tests automatizados con `pytest` y Playwright E2E |
| **Docker** | Dockerfile con extras `.[audit]` para despliegue en contenedor |


## Inicio rápido

```bash
# 1. Instalar dependencias
pip install -e ".[dev,audit]"

# 2. Configurar token de GitHub (para el scraper)
echo "GITHUB_TOKEN=ghp_tu_token_aqui" > .env

# 3a. Usar el CLI directamente
wheelsaver stats                          # Estadísticas de la BD
wheelsaver search fastapi pytest          # Buscar repos por keyword
wheelsaver swap "pdf parser"              # Buscar alternativas
wheelsaver ready                          # Checklist del proyecto
wheelsaver audit-code .                   # Auditoría de seguridad y calidad

# 3b. Lanzar API REST (modo desarrollo)
wheelsaver api --dev                      # → http://localhost:8000/docs
```

## Programación de Actualización Local (Windows / Linux)

Para actualizar la BD local automáticamente 2 veces por semana a la 1:00 AM (sin interrumpir tu jornada laboral):

### Windows (PowerShell):
```powershell
$Action = New-ScheduledTaskAction -Execute "wheelsaver" -Argument "scrape --min-stars 500"
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Tuesday,Friday -At "01:00AM"
Register-ScheduledTask -TaskName "WheelSaver_AutoScrape" -Action $Action -Trigger $Trigger -Description "Actualización automática de BD WheelSaver los martes y viernes a la 1:00 AM"
```

## Skills para IA (Claude Code / Antigravity)

Instala las rueditas de entrenamiento en cualquier proyecto:

```powershell
.\Instalar-WheelSaver.ps1
```

Luego abre la IA en cualquier proyecto y usa:

| Comando | Qué hace |
|---|---|
| `Audita este proyecto con WheelSaver` | Auditoría completa con matriz de scoring |
| `wheel-ready` | Checklist de lo que le falta al proyecto |
| `wheel-swap parser de PDF` | Busca si ya existe una librería para lo que codeas |

## Arquitectura

```
WheelSaver/
├── cli.py                    # CLI unificado (Typer + Rich con soporte UTF-8)
├── api/main.py               # API REST FastAPI + Web UI estática
├── api/llm.py                # Failover Multi-LLM (Groq, Cerebras, Gemini, OpenRouter, etc.) con timeout global de 45s y caché
├── scraper/
│   ├── github_fetcher.py     # Scraper GraphQL (httpx)
│   └── db_manager.py         # ORM SQLite + FTS5 + Live Fallback API
├── scripts/
│   ├── import_from_evanli.py # Importador EvanLi
│   └── scrape_gitstar_ranking.py  # Scraper gitstar-ranking
├── services/
│   ├── project_auditor.py    # Detector modular de stack del proyecto
│   └── static_analyzer.py    # Análisis estático (bandit + vulture + radon)
├── .agents/skills/
│   ├── wheel_saver/          # Skill: auditoría completa
│   ├── wheel-ready/          # Skill: checklist de proyecto
│   └── wheel-swap/           # Skill: busca alternativas
├── frontend/                 # UI web (HTML + CSS + JS dinámico, responsive mobile)
├── tests/                    # 80+ tests con pytest + Playwright E2E + CI GitHub Actions
├── Dockerfile                # Contenedor Python slim con extras de auditoría
└── pyproject.toml            # Config del proyecto v3.3.1
```

## Comandos del CLI

```bash
wheelsaver search <keywords>   # Búsqueda FTS5 con Rich Table
wheelsaver stats               # Estadísticas con Panels
wheelsaver scrape              # Scraper GraphQL desde Top 1
wheelsaver import evanli       # Importar EvanLi
wheelsaver import gitstar      # Importar gitstar-ranking
wheelsaver api                 # Lanzar API REST (127.0.0.1 por defecto, --dev para reload)
wheelsaver docker              # Levantar en Docker
wheelsaver ready               # Checklist + análisis estático del proyecto
wheelsaver audit-code <ruta>   # Seguridad, código muerto y complejidad
wheelsaver swap <feature>      # Buscar alternativas
wheelsaver skillify <repo>     # Convertir repo en skill de IA
wheelsaver ask <pregunta>      # Consultar a la IA con RAG
```

---

> Hecho con 🛞 para no reinventar la rueda.

