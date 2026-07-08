# WheelSaver

WheelSaver es un sistema que descarga periódicamente los mejores repositorios de GitHub y los almacena en una base de datos local SQLite. 
Además, incluye una **IA Skill** nativa para que tu asistente pueda auditar tus proyectos y recomendarte librerías, evitando que "reinventes la rueda".

## Componentes

1. **Scraper (Recolección de datos)**: Script en Python (`scraper/github_fetcher.py`) que usa la API GraphQL de GitHub para buscar repositorios con más de 500 estrellas.
2. **Base de Datos Local**: Los datos se almacenan en `data/top_repos.db`.
3. **GitHub Actions**: Automatiza la ejecución del scraper cada semana (`.github/workflows/update-db.yml`).
4. **IA Skill**: Integración nativa con tu Asistente de IA ubicada en `.agents/skills/wheel_saver`.

## Requisitos
- Python 3.10+
- Token de acceso personal de GitHub (PAT)

## Configuración Local
1. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
2. Rellena el archivo `.env` con tu `GITHUB_TOKEN`.
3. Ejecuta el scraper (opcional, para llenar la base de datos inicialmente):
   ```bash
   python scraper/github_fetcher.py
   ```

## Cómo usar la Skill de Auditoría
Simplemente abre tu asistente de IA (como lo estás usando ahora) y dile:
> *"Audita este proyecto usando WheelSaver"*

El asistente analizará tu código, extraerá palabras clave de lo que estás intentando construir y buscará en `data/top_repos.db` las mejores librerías que te ahorrarán tiempo.

## Configuración en GitHub
Para que se actualice automáticamente en la nube:
1. Crea un repositorio en GitHub y sube este código.
2. Ve a `Settings` > `Secrets and variables` > `Actions`.
3. Añade un nuevo secreto llamado `PAT_GITHUB_TOKEN` y pega tu token de GitHub.
