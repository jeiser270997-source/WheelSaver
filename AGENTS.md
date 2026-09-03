# AGENTS.md — WHEELSAVER (CAVEMAN Ultra)

> Read first. Core instructions, architecture, operational rules, and invariants.
> Contexto completo del proyecto: `CLAUDE.md`.

## ⛔ GOLDEN FREEZE v3.3.2 (2026-08-15)

- **ESTADO: CONGELADO**. Checkpoint GOLDEN: **102/102 tests PASS** (85 pytest + 17 node).
- **MANDATO**: NO code changes sin trigger real (bug reproducible o test
  fallando) + doble confirmación del usuario + suite completa en verde.
- **MODELO REACTIVO**: sin GitHub Actions ni CI (workflow eliminado 2026-08-15).
  La DB se actualiza BAJO DEMANDA: `wheelsaver update` o automáticamente en
  search/swap/stats si está desactualizada (>7d). Nunca jobs programados.
- **Protegidos**: `scraper/**`, `api/**`, `services/**`, `cli.py`,
  `mcp_server.js`, `mcp_helpers.js`, `frontend/**`.
- **Workflow**: si hay trigger real → fix → `pytest` + `node --test` en verde
  → actualizar este bloque con el nuevo contador → commit.
- **Checkpoint**: auditado 2026-09-02 + reactivo.
  DB real: `data/top_repos.db` — **21,522 repos** FTS5.
- **Nota**: `node_modules/` NO está trackeado. Requiere `npm install` una vez
  para el MCP (`better-sqlite3` + `@modelcontextprotocol/sdk`).

## ECOSYSTEM (2026-08-15)

- WHEELSAVER = **biblioteca de código**: 20k+ repos GitHub FTS5 local, $0.
- Proporciona skills/alternativas a los otros 3 proyectos por **contratos de
  datos** (lee `data/top_repos.db`, nunca código compartido):
  - Faceless: `services/wheel_*.js` leen la DB real vía better-sqlite3.
  - Asistente: MCP `wheelsaver` → repo real (duplicado interno eliminado).
  - Scrapper: búsqueda de librerías para el harvester.
- Mapa completo: `E:\PROYECTOS\Mis_Proyectos\faceless-bot TERMINADO\docs\ECOSYSTEM.md`

## MCP (6 herramientas)

`wheelsaver_search`, `wheelsaver_swap`, `wheelsaver_top`, `wheelsaver_languages`,
`wheelsaver_stats`, `wheelsaver_update` (actualiza bajo demanda; search/top/stats
avisan si la DB está desactualizada). DB real: `data/top_repos.db` (FTS5).
