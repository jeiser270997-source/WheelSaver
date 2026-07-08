---
name: WheelSaver Auditor
description: Audita el proyecto actual, lee los requerimientos y busca en la base de datos local (top_repos.db) los repositorios de GitHub más populares que podrían servir como librerías o herramientas para evitar reinventar la rueda.
---

# WheelSaver Auditor Skill

Esta skill te permite (como Asistente de IA) auditar el proyecto actual del usuario y recomendarle repositorios Top de GitHub que ya resuelven los problemas que está intentando solucionar, basados en el contexto local.

## Instrucciones para el Agente (IA)

Cuando el usuario invoque esta skill (ej. "Audita mi proyecto con WheelSaver"):

1. **Analiza el Proyecto Local:**
   - Lee archivos importantes como `package.json`, `requirements.txt`, `README.md`, o inspecciona la estructura de directorios (`list_dir`) para entender el objetivo del proyecto, las tecnologías usadas y qué características está intentando construir el usuario.
   
2. **Extrae Palabras Clave (Keywords):**
   - Piensa en 3 a 5 palabras clave técnicas o tópicos relacionados con lo que el proyecto necesita (ej., `auth`, `ui-components`, `database`, `scraper`, `websocket`).

3. **Busca en la Base de Datos Local:**
   - Usa el script `scripts/search_db.py` (ubicado dentro de la carpeta de esta skill) para consultar la base de datos SQLite `data/top_repos.db` (en la raíz del workspace de WheelSaver).
   - Comando a ejecutar: `python .agents/skills/wheel_saver/scripts/search_db.py <keyword1> <keyword2>`
   
4. **Filtra y Selecciona:**
   - Lee el JSON resultante de la búsqueda.
   - Selecciona los 3 a 5 repositorios más relevantes que verdaderamente le ahorrarían tiempo al usuario (no le recomiendes React si ya usa React, recomiéndale librerías específicas para los problemas que quiere resolver).
   
5. **Presenta el Reporte:**
   - Crea un reporte detallado al usuario usando un artefacto (artifact) Markdown llamado `wheelsaver_audit_report.md`.
   - Incluye:
     - Resumen de lo que entendiste de su proyecto.
     - Lista de Repositorios Top recomendados (Nombre, Estrellas, Descripción, URL).
     - Por qué recomiendas cada uno y cómo debería integrarlo en lugar de programarlo desde cero.
