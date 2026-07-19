# 🛞 WheelSaver

**Tu biblioteca offline de GitHub + 3 skills de IA para no reinventar la rueda.**

WheelSaver descarga automaticamente los mejores repositorios de GitHub (>500⭐)
y los almacena en una base de datos SQLite local con busqueda FTS5 ultrarrápida.
Incluye skills nativos para Claude Code que auditan tus proyectos y te recomiendan
librerias existentes, evitando que codees desde cero lo que ya esta resuelto.

```
📦 23,621 repos · 🌐 142 lenguajes · ⚡ Busqueda FTS5 en milisegundos
```

## Componentes

| Componente | Que hace |
|---|---|
| **3 Scrapers** | GitHub GraphQL API + EvanLi/Github-Ranking + gitstar-ranking.com |
| **Base de datos** | SQLite + FTS5, actualizacion semanal via GitHub Actions |
| **CLI unificado** | 11 comandos con Typer + Rich (tablas, colores, autocompletado) |
| **API REST** | FastAPI con 9+ endpoints + Swagger en `/docs` |
| **3 Skills IA** | `wheel_saver` `wheel-ready` `wheel-swap` para Claude Code |
| **Docker** | Dockerfile para despliegue en contenedor |

## Inicio rapido

```bash
# 1. Instalar dependencias
pip install -e .

# 2. Configurar token de GitHub (para el scraper)
echo "GITHUB_TOKEN=ghp_tu_token_aqui" > .env

# 3a. Usar el CLI directamente
wheelsaver stats                          # Estadisticas de la BD
wheelsaver search fastapi pytest          # Buscar repos por keyword
wheelsaver swap "pdf parser"              # Buscar alternativas
wheelsaver ready                          # Checklist del proyecto

# 3b. Lanzar API REST
wheelsaver api                            # → http://localhost:8000/docs
```

## Skills para Claude Code

Instala las rueditas de entrenamiento en cualquier proyecto:

```powershell
.\Instalar-WheelSaver.ps1
```

Luego abre `claude` y usa:

| Comando | Que hace |
|---|---|
| `Audita este proyecto con WheelSaver` | Auditoria completa con matriz de scoring |
| `wheel-ready` | Checklist de lo que le falta al proyecto |
| `wheel-swap parser de PDF` | Busca si ya existe una libreria para lo que codeas |

## Arquitectura

```
WheelSaver/
├── cli.py                    # CLI unificado (Typer + Rich)
├── api/main.py               # API REST FastAPI
├── scraper/
│   ├── github_fetcher.py     # Scraper GraphQL (httpx)
│   └── db_manager.py         # ORM SQLite + FTS5
├── scripts/
│   ├── import_from_evanli.py # Importador EvanLi
│   └── scrape_gitstar_ranking.py  # Scraper gitstar-ranking
├── services/
│   └── project_auditor.py    # Detector de stack del proyecto
├── .agents/skills/
│   ├── wheel_saver/          # Skill: auditoria completa
│   ├── wheel-ready/          # Skill: checklist de proyecto
│   └── wheel-swap/           # Skill: busca alternativas
├── frontend/                 # UI web (HTML + CSS + JS)
├── tests/                    # Tests con pytest
├── Dockerfile                # Contenedor Python slim
└── pyproject.toml            # Config del proyecto
```

## Comandos del CLI

```bash
wheelsaver search <keywords>   # Busqueda FTS5 con Rich Table
wheelsaver stats               # Estadisticas con Panels
wheelsaver scrape              # Scraper GraphQL desde Top 1
wheelsaver import evanli       # Importar EvanLi
wheelsaver import gitstar      # Importar gitstar-ranking
wheelsaver api                 # Lanzar API REST
wheelsaver docker              # Levantar en Docker
wheelsaver ready               # Checklist del proyecto
wheelsaver swap <feature>      # Buscar alternativas
wheelsaver skillify <repo>     # Convertir repo en skill de IA
wheelsaver ask <pregunta>      # Consultar a la IA con RAG
```

## Configuracion en GitHub

Para actualizacion automatica semanal:
1. sube el codigo a GitHub
2. Ve a `Settings` > `Secrets and variables` > `Actions`
3. Anade un secreto llamado `PAT_GITHUB_TOKEN` con tu token de GitHub

---

> Hecho con 🛞 para no reinventar la rueda.
