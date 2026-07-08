---
name: WheelSaver Auditor
description: Audita el proyecto actual, lee los requerimientos y busca en la base de datos local (top_repos.db) los repositorios de GitHub más populares que podrían servir como librerías o herramientas para evitar reinventar la rueda.
---

# WheelSaver Auditor — Instrucciones para el Agente de IA

Cuando el usuario te diga frases como "Audita mi proyecto con WheelSaver",
"WheelSaver, qué me recomiendas", "no quiero reinventar la rueda en X", etc.,
debes ejecutar este flujo completo de 5 pasos.

---

## PASO 1 — Escanear el Proyecto

Inspecciona el directorio del proyecto del usuario. Busca y lee estos archivos:

- `package.json` / `package-lock.json` — dependencias JS/Node
- `requirements.txt` / `pyproject.toml` / `Pipfile` — dependencias Python
- `pom.xml` / `build.gradle` — dependencias Java
- `Cargo.toml` — dependencias Rust
- `go.mod` — dependencias Go
- `README.md` — descripcion del proyecto
- `*.md` — documentacion adicional
- Estructura de carpetas general (hasta 2 niveles)

**Objetivo**: Entender:
1. Que hace el proyecto? (proposito)
2. Que tecnologias/lenguajes usa ya?
3. Que funcionalidades esta intentando construir o tiene pendientes?
4. Cuales son sus puntos de dolor o partes complejas?

---

## PASO 2 — Extraer Keywords Inteligentes

Con base en lo que entendiste, extrae **5 a 10 keywords tecnicas** que capturen
lo que el proyecto **necesita pero no tiene**. Piensa como un desarrollador
experimentado:

- **No pongas lo que ya usa** (si usa React, no pongas "react")
- **Si pon** lo que le falta, lo que esta construyendo desde cero, o lo que
  podria mejorar con una libreria existente
- Usa terminos en **ingles** (como aparecen en los topics de GitHub)
- Ejemplos de buenas keywords: `auth`, `websocket`, `state-management`, `orm`,
  `pdf-generator`, `rest-api`, `testing`, `caching`, `queue`, `i18n`,
  `charting`, `file-upload`, `cli`, `scraping`, `monitoring`, `security`

### Categorias de auditoria:
Considera keywords de estas categorias:

| Categoria | Ejemplos de keywords |
|---|---|
| **Seguridad** | auth, encryption, cors, csrf, secrets, ssl, oauth, jwt |
| **Performance** | caching, async, queue, streaming, indexing, cdn |
| **Testing** | pytest, jest, cypress, mocking, coverage, e2e |
| **UI/UX** | components, design-system, animation, forms, charts |
| **DevOps** | docker, ci/cd, monitoring, deployment, logging |
| **Datos** | orm, validation, migration, serialization, queue |
| **CLI/Tooling** | argument-parser, progress-bar, logging, config, dotenv |

---

## PASO 3 — Buscar en la Base de Datos Local

Ejecuta el CLI unificado de busqueda con las keywords extraidas:

```
python cli.py search keyword1 keyword2 keyword3 --limit 25
```

El script `cli.py` resuelve automaticamente la ubicacion de la base de datos.
Devuelve resultados ordenados por estrellas con: `name`, `owner`, `description`,
`url`, `stars`, `language`, `topics`.

Si el CLI no esta disponible, usa el script legacy:
```
python .agents/skills/wheel_saver/scripts/search_db.py keyword1 keyword2
```

**Importante**: Si la BD existe pero tiene menos de 100 repos, avisa al usuario
que ejecute primero el scraper: `python cli.py scrape`

---

## PASO 4 — Filtrar y Analizar Resultados

Del resultado JSON, selecciona los **5 a 8 repositorios mas relevantes**.

### Matriz de puntuacion:

| Criterio | Peso | Descripcion |
|---|---|---|
| Resuelve directamente un problema | 10 ptos | El repo hace exactamente lo que el proyecto necesita |
| Estrellas | Segun rango | +50k = 10ptos, +10k = 8ptos, +5k = 6ptos, +1k = 4ptos |
| Lenguaje compatible | 8 ptos | Mismo lenguaje + ecosistema |
| Activo ultimos 12 meses | 5 ptos | Commits recientes, issues respondidos |
| Topics relacionados | 5 ptos | Coincidencia con keywords del proyecto |
| Especifico vs generico | 5 ptos | Preferir solucion enfocada sobre todologo |

Suma los puntos y selecciona los de mayor puntuacion.

### Estratificacion por estrellas:
- **50,000+** estrellas: "Estandar de la industria, adopcion masiva"
- **10,000-50,000** estrellas: "Muy solido, bien mantenido"
- **5,000-10,000** estrellas: "Solido, comunidad activa"
- **1,000-5,000** estrellas: "Emergente, verificar mantenimiento"

### Descarta repositorios que:
- Ya esten siendo usados en el proyecto
- Sean listas de recursos (`awesome-*`) a menos que el usuario explore opciones
- Sean redundantes entre si (no recomiendes 3 librerias que hacen lo mismo)
- No tengan actividad en los ultimos 12 meses
- Tengan licencia incompatible con el proyecto del usuario

---

## PASO 5 — Generar el Reporte de Auditoria

Crea un **artefacto Markdown** llamado `wheelsaver_audit_[nombre_proyecto].md`
con el siguiente formato:

```markdown
# WheelSaver Audit — [Nombre del Proyecto]
> Auditado el [fecha] | [N] repos analizados en la base de datos

## Lo que entendi de tu proyecto
[Descripcion breve: que hace, stack actual, que esta construyendo]

## Resumen de la Busqueda
- Keywords analizadas: `keyword1`, `keyword2`, ...
- Repos encontrados: X
- Recomendaciones finales: Y
- Scoring: [relevance/10]

---

## Recomendaciones

### 1. [Nombre del Repo] — [Estrellas] ⭐
**URL**: https://github.com/owner/repo
**Categoria**: [seguridad | performance | testing | ui | datos | devops | cli]
**Score**: [puntuacion]/10
**Por que te sirve**: [Explicacion concreta de por que resuelve un problema]
**Como integrarlo**: [Comando de instalacion exacto]
**Tags**: `tag1`, `tag2`

### 2. ...

---

## Quick Wins (Alto impacto, bajo esfuerzo)
1. [Accion concreta #1] — [estimacion: minutos/horas]

## Arquitectura (Cambios estructurales)
1. [Accion concreta #2] — [estimacion: dias]

## Deuda Tecnica (Riesgos a futuro)
1. [Practica actual riesgosa] → [solucion recomendada]
```

### Secciones del reporte explicadas:

- **Quick Wins**: Recomendaciones que se pueden implementar en minutos (instalar
  una libreria, agregar config). Prioridad maxima.
- **Arquitectura**: Cambios que requieren repensar el diseno (migrar a un
  framework, agregar una capa de abstraccion). Impacto alto, esfuerzo medio.
- **Deuda Tecnica**: Practicas actuales que van a doler en el futuro (codigo
  manual que deberia ser libreria, dependencias deprecadas, falta de tests).

---

## Criterios de Auditoria Avanzados

### Checklist de auditoria:
1. [ ] Identificar dependencias actuales (package.json, requirements.txt, etc.)
2. [ ] Identificar funcionalidades implementadas manualmente
3. [ ] Detectar dependencias deprecadas o mal mantenidas
4. [ ] Buscar keywords en BD local (cli.py search)
5. [ ] Evaluar cada recomendacion contra stack actual
6. [ ] Verificar actividad reciente (12 meses)
7. [ ] Verificar licencia compatible
8. [ ] Priorizar por puntuacion de matriz
9. [ ] Generar reporte con secciones Quick Wins, Arquitectura, Deuda Tecnica

### Sugerencias de reemplazo:
Si el proyecto usa alguna dependencia que tiene una alternativa mas popular
o mejor mantenida en la BD, sugierela explicitamente:
- "Actualmente usas X, pero [repo] tiene [N] estrellas mas y resuelve [problema]"

### Integracion con API:
Si la API REST de WheelSaver esta corriendo (puerto 8000), puedes consultarla
directamente via HTTP en vez del CLI:
```
curl http://localhost:8000/search?q=keyword&limit=10
curl http://localhost:8000/stats
curl http://localhost:8000/languages
```

---

## Notas Importantes para el Agente

- La base de datos se encuentra en `data/top_repos.db` dentro del proyecto
  WheelSaver (resuelta automaticamente por el CLI)
- Contiene repos con **+1,000 estrellas** de todos los lenguajes y categorias
- Se auto-actualiza cada semana con GitHub Actions (3 fuentes: GraphQL API,
  EvanLi/Github-Ranking, gitstar-ranking.com)
- Si la API local esta corriendo, usar HTTP es mas rapido que CLI
- Siempre que puedas, da el comando exacto de instalacion (`npm install X`,
  `pip install X`, `cargo add X`, etc.)
- Se honesto si ningun repo en la BD calza perfecto — mejor decirlo que
  recomendar algo forzado
- Para usar el CLI unificado: `python cli.py search <keywords> --limit 25`
- Para ver estadisticas: `python cli.py stats`
