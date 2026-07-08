---
name: WheelSaver Auditor
description: Audita el proyecto actual, lee los requerimientos y busca en la base de datos local (top_repos.db) los repositorios de GitHub más populares que podrían servir como librerías o herramientas para evitar reinventar la rueda.
---

# WheelSaver Auditor — Instrucciones para el Agente de IA

Cuando el usuario te diga frases como "Audita mi proyecto con WheelSaver", "WheelSaver, qué me recomiendas", "no quiero reinventar la rueda en X", etc., debes ejecutar este flujo completo.

---

## PASO 1 — Escanear el Proyecto

Inspecciona el directorio del proyecto que te indica el usuario usando `list_dir` y `view_file`. Busca y lee los siguientes archivos si existen:

- `package.json` / `package-lock.json` — dependencias JavaScript/Node
- `requirements.txt` / `pyproject.toml` / `Pipfile` — dependencias Python
- `pom.xml` / `build.gradle` — dependencias Java
- `Cargo.toml` — dependencias Rust
- `go.mod` — dependencias Go
- `README.md` — descripción del proyecto
- `*.md` archivos de documentación
- Estructura de carpetas general (hasta 2 niveles de profundidad)

**Objetivo del PASO 1**: Entender:
1. ¿Qué hace el proyecto? (propósito)
2. ¿Qué tecnologías/lenguajes usa ya?
3. ¿Qué funcionalidades está intentando construir o tiene pendientes?
4. ¿Cuáles son sus puntos de dolor o partes complejas?

---

## PASO 2 — Extraer Keywords Inteligentes

Con base en lo que entendiste, extrae **5 a 10 keywords técnicas** que capturen lo que el proyecto necesita. Piensa como un desarrollador experimentado:

- **No pongas lo que ya usa** (si usa React, no pongas "react")
- **Sí pon** lo que le falta, lo que está intentando construir desde cero, o lo que podría mejorar
- Usa términos en **inglés** (como aparecen en los topics de GitHub)
- Ejemplos de buenos keywords: `auth`, `websocket`, `state-management`, `orm`, `pdf-generator`, `rest-api`, `testing`, `caching`, `queue`, `i18n`, `charting`, `file-upload`, `cli`, `scraping`

---

## PASO 3 — Buscar en la Base de Datos Local

Ejecuta el script de búsqueda para cada keyword usando `run_command`. La base de datos contiene repositorios con +1,000 estrellas.

**Ruta del script (relativa al workspace de WheelSaver):**
```
e:\PROYECTOS\Mis_Proyectos\TOP_REPOS\.agents\skills\wheel_saver\scripts\search_db.py
```

**Comando a ejecutar (PowerShell):**
```powershell
python "e:\PROYECTOS\Mis_Proyectos\TOP_REPOS\.agents\skills\wheel_saver\scripts\search_db.py" keyword1 keyword2 keyword3 keyword4 keyword5
```

El script devuelve un JSON con los repos encontrados ordenados por estrellas, con campos: `name`, `owner`, `description`, `url`, `stars`, `language`, `topics`.

---

## PASO 4 — Filtrar y Analizar Resultados

Del JSON devuelto, selecciona los **5 a 8 repositorios más relevantes** para el proyecto auditado. Aplica este criterio de selección:

| Criterio | Prioridad |
|---|---|
| Resuelve directamente un problema del proyecto | Alta |
| Tiene +10,000 estrellas | Alta |
| Lenguaje compatible con el proyecto | Alta |
| Activo en los últimos 12 meses | Media |
| Tiene topics relacionados con el proyecto | Media |
| Es más específico que genérico | Media |

**Descarta** repositorios que:
- Ya estén siendo usados en el proyecto
- Sean listas de recursos (tipo `awesome-*`) a menos que el usuario no sepa por dónde empezar
- Sean redundantes entre sí (no recomiendes 3 librerías que hacen lo mismo)

---

## PASO 5 — Generar el Reporte de Auditoría

Crea un **artefacto Markdown** llamado `wheelsaver_audit_[nombre_proyecto].md` con el siguiente formato:

```markdown
# WheelSaver Audit — [Nombre del Proyecto]
> Auditado el [fecha] | [N] repos analizados en la base de datos

## Lo que entendí de tu proyecto
[Descripción breve de qué hace el proyecto, stack actual, y qué está tratando de construir]

## Resumen de la Búsqueda
- Keywords analizadas: `keyword1`, `keyword2`, ...
- Repos encontrados: X
- Recomendaciones finales: Y

---

## Recomendaciones

### 1. [Nombre del Repo] — [Estrellas] ⭐
**URL**: https://github.com/owner/repo  
**Por qué te sirve**: [Explicación concreta de por qué este repo resuelve un problema específico del proyecto auditado]  
**Cómo integrarlo**: [Instrucción de instalación o uso rápido]  
**Tags**: `tag1`, `tag2`

### 2. ...

---

## Acciones Recomendadas
1. [Acción concreta #1]
2. [Acción concreta #2]
...
```

---

## Notas Importantes para el Agente

- La base de datos se encuentra en `e:\PROYECTOS\Mis_Proyectos\TOP_REPOS\data\top_repos.db`
- Contiene repos con **+1,000 estrellas** de todos los lenguajes y categorías
- Se auto-actualiza cada semana con GitHub Actions
- Si la BD está vacía o tiene menos de 100 repos, avisa al usuario que ejecute el scraper primero con `python scraper/github_fetcher.py` desde la carpeta de WheelSaver
- Siempre que puedas, da el comando exacto de instalación (`npm install X`, `pip install X`, etc.)
- Sé honesto si ningún repo en la BD calza perfecto — mejor decirlo que recomendar algo forzado
