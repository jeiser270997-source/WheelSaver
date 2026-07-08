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
| **CLI unificado** | 9 comandos con Typer + Rich (tablas, colores, autocompletado) |
| **API REST** | FastAPI con 6 endpoints + Swagger en `/docs` |
| **Dashboard** | Streamlit interactivo con graficos y busqueda |
| **3 Skills IA** | `wheel-audit` `wheel-ready` `wheel-swap` para Claude Code |
| **Docker** | Dockerfile + compose, despliegue en 1 comando |

## Inicio rapido

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Configurar token de GitHub (para el scraper)
echo "GITHUB_TOKEN=ghp_tu_token_aqui" > .env

# 3a. Usar el CLI directamente
python cli.py stats                          # Estadisticas de la BD
python cli.py search fastapi pytest          # Buscar repos por keyword
python cli.py swap "pdf parser"              # Buscar alternativas
python cli.py ready                          # Checklist del proyecto

# 3b. Lanzar API REST
python cli.py api                            # → http://localhost:8000/docs

# 3c. Lanzar Dashboard
python cli.py dashboard                      # → http://localhost:8501

# 3d. Modo Docker
docker compose up --build -d                 # → http://localhost:8000
```

## Skills para Claude Code

Instala las rueditas de entrenamiento en cualquier proyecto:

```powershell
& "E:\PROYECTOS\Mis_Proyectos\TOP_REPOS\Instalar-WheelSaver.ps1"
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
├── dashboard.py              # Dashboard Streamlit
├── api/main.py               # API REST FastAPI
├── scraper/
│   ├── github_fetcher.py     # Scraper GraphQL (httpx)
│   └── db_manager.py         # ORM SQLite + FTS5
├── scripts/
│   ├── import_from_evanli.py # Importador EvanLi
│   └── scrape_gitstar_ranking.py  # Scraper gitstar-ranking
├── .agents/skills/
│   ├── wheel_saver/          # Skill: auditoria completa
│   ├── wheel-ready/          # Skill: checklist de proyecto
│   └── wheel-swap/           # Skill: busca alternativas
├── tests/                    # 18 tests con pytest
├── data/top_repos.db         # BD SQLite (~23k repos)
├── Dockerfile                # Contenedor Python slim
└── docker-compose.yml        # Orquestacion Docker
```

## Comandos del CLI

```bash
python cli.py search <keywords>   # Busqueda FTS5 con Rich Table
python cli.py stats               # Estadisticas con Panels
python cli.py scrape              # Scraper GraphQL desde Top 1
python cli.py import evanli       # Importar EvanLi
python cli.py import gitstar      # Importar gitstar-ranking
python cli.py api                 # Lanzar API REST
python cli.py docker              # Levantar en Docker
python cli.py dashboard           # Lanzar Dashboard
python cli.py ready               # Checklist del proyecto
python cli.py swap <feature>      # Buscar alternativas
python cli.py --install-completion  # Autocompletado
```

## Configuracion en GitHub

Para actualizacion automatica semanal:
1. sube el codigo a GitHub
2. Ve a `Settings` > `Secrets and variables` > `Actions`
3. Anade un secreto llamado `PAT_GITHUB_TOKEN` con tu token de GitHub

---

> Hecho con 🛞 para no reinventar la rueda.
