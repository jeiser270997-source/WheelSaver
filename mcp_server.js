/**
 * WheelSaver/mcp_server.js
 * Servidor MCP nativo para WheelSaver — Biblioteca GitHub del ecosistema (20k+ repos, FTS5).
 *
 * Tools:
 *  - wheelsaver_search     búsqueda FTS5 por keywords (language, min_stars, limit)
 *  - wheelsaver_top        top repos por estrellas (language opcional)
 *  - wheelsaver_swap       busca alternativas a una librería/feature (alias de search)
 *  - wheelsaver_languages  lenguajes más usados en la DB
 *  - wheelsaver_stats      estadísticas de la DB real
 */
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const Database = require('better-sqlite3');
const { Server } = require('@modelcontextprotocol/sdk/server/index.js');
const { StdioServerTransport } = require('@modelcontextprotocol/sdk/server/stdio.js');
const { CallToolRequestSchema, ListToolsRequestSchema } = require('@modelcontextprotocol/sdk/types.js');

const {
  resolveDbPath,
  buildSearchQuery,
  buildTopSql,
  buildStatsSql,
  buildLanguagesSql,
  formatRepoRows,
  formatStatsRow,
} = require('./mcp_helpers.js');

const ROOT = __dirname;
const DB_PATH = resolveDbPath(ROOT);
// Fallback: copia global instalada (pip install -e . → ~/.wheelsaver/top_repos.db)
const GLOBAL_DB = path.join(os.homedir(), '.wheelsaver', 'top_repos.db');

function getDbPath() {
  if (fs.existsSync(DB_PATH)) return DB_PATH;
  if (fs.existsSync(GLOBAL_DB)) return GLOBAL_DB;
  return DB_PATH;
}

function getDB() {
  const p = getDbPath();
  if (!fs.existsSync(p)) return null;
  try {
    return new Database(p, { readonly: true });
  } catch {
    return null;
  }
}

function ok(text) {
  return { content: [{ type: 'text', text: String(text) }] };
}
function err(text) {
  return { content: [{ type: 'text', text: `❌ ${text}` }], isError: true };
}

function queryAll(db, sql, params) {
  try {
    return db.prepare(sql).all(...params);
  } catch (e) {
    return { __error: e.message };
  }
}

const TOOLS = [
  {
    name: 'wheelsaver_search',
    description: 'Busca repositorios GitHub en la biblioteca local de WheelSaver (20k+ repos, FTS5 offline). Para encontrar librerías, herramientas o proyectos por keywords, lenguaje o estrellas mínimas.',
    inputSchema: {
      type: 'object',
      properties: {
        keywords: {
          type: 'array',
          items: { type: 'string' },
          description: 'Palabras clave (ej: ["tts", "voice", "clone"])',
        },
        language: { type: 'string', description: 'Filtrar por lenguaje (ej: "Python", "TypeScript")' },
        min_stars: { type: 'number', description: 'Estrellas mínimas' },
        limit: { type: 'number', description: 'Máximo de resultados (default: 10)' },
      },
      required: ['keywords'],
    },
  },
  {
    name: 'wheelsaver_swap',
    description: 'Busca alternativas ya existentes a una librería o feature que quieras implementar (evita reinventar la rueda).',
    inputSchema: {
      type: 'object',
      properties: {
        feature: { type: 'string', description: 'Feature o librería a reemplazar (ej: "pdf parser", "voice cloning")' },
        language: { type: 'string', description: 'Filtrar por lenguaje' },
        limit: { type: 'number', description: 'Máximo de resultados (default: 8)' },
      },
      required: ['feature'],
    },
  },
  {
    name: 'wheelsaver_top',
    description: 'Top repositorios por estrellas (con filtro de lenguaje opcional).',
    inputSchema: {
      type: 'object',
      properties: {
        language: { type: 'string', description: 'Filtrar por lenguaje (ej: "Python")' },
        limit: { type: 'number', description: 'Máximo de resultados (default: 10)' },
      },
      required: [],
    },
  },
  {
    name: 'wheelsaver_languages',
    description: 'Lenguajes más usados en la biblioteca local de WheelSaver.',
    inputSchema: {
      type: 'object',
      properties: {
        limit: { type: 'number', description: 'Máximo de lenguajes (default: 10)' },
      },
      required: [],
    },
  },
  {
    name: 'wheelsaver_stats',
    description: 'Estadísticas de la biblioteca local (total repos, lenguajes, estrellas).',
    inputSchema: { type: 'object', properties: {}, required: [] },
  },
];

async function executeTool(name, args) {
  const db = getDB();
  try {
    switch (name) {
      case 'wheelsaver_search':
      case 'wheelsaver_swap': {
        if (!db) return err('DB no encontrada. Corré `wheelsaver scrape` o verificá data/top_repos.db.');
        const raw = name === 'wheelsaver_swap' ? [String(args.feature || '')] : (args.keywords || []);
        const keywords = Array.isArray(raw) ? raw.map(String) : [String(raw)];
        const { sql, params } = buildSearchQuery(keywords, args.language || null, args.min_stars ?? null, Number(args.limit ?? 10));
        const rows = queryAll(db, sql, params);
        if (rows.__error) return err(`Error de consulta: ${rows.__error}`);
        const prefix = name === 'wheelsaver_swap' ? '🔁 Alternativas encontradas' : '🔍 Resultados de WheelSaver';
        return ok(`${prefix} (${rows.length}):\n\n${formatRepoRows(rows) || 'Sin coincidencias. Probá otros keywords.'}`);
      }

      case 'wheelsaver_top': {
        if (!db) return err('DB no encontrada.');
        const { sql, params } = buildTopSql(args.language || null, Number(args.limit ?? 10));
        const rows = queryAll(db, sql, params);
        if (rows.__error) return err(`Error de consulta: ${rows.__error}`);
        return ok(`🏆 Top repos${args.language ? ` (${args.language})` : ''}:\n\n${formatRepoRows(rows)}`);
      }

      case 'wheelsaver_languages': {
        if (!db) return err('DB no encontrada.');
        const { sql, params } = buildLanguagesSql(Number(args.limit ?? 10));
        const rows = queryAll(db, sql, params);
        if (rows.__error) return err(`Error de consulta: ${rows.__error}`);
        const lines = rows.map((r, i) => `${i + 1}. **${r.language}** — ${r.repos} repos`);
        return ok(`🌐 Lenguajes más usados:\n\n${lines.join('\n')}`);
      }

      case 'wheelsaver_stats': {
        const p = getDbPath();
        if (!db) return ok(`📊 WheelSaver — Estado:\n- Base de Datos: ❌ No encontrada (${p})\n- Corré: wheelsaver scrape --min-stars 500`);
        const { sql, params } = buildStatsSql();
        const rows = queryAll(db, sql, params);
        if (rows.__error) return err(`Error de consulta: ${rows.__error}`);
        return ok(`📊 WheelSaver — Estado:\n- Base de Datos: ✅ OK (${p})\n- ${formatStatsRow(rows[0])}\n- Modo: $0 Local-First · Biblioteca GitHub del ecosistema`);
      }

      default:
        return err(`Herramienta desconocida: ${name}`);
    }
  } finally {
    if (db) db.close();
  }
}

async function main() {
  const server = new Server(
    { name: 'wheelsaver-mcp', version: '3.3.2' },
    { capabilities: { tools: {} } }
  );
  server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: TOOLS }));
  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    try {
      return await executeTool(name, args || {});
    } catch (e) {
      return err(`Error interno en "${name}": ${e.message}`);
    }
  });
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((e) => {
  process.stderr.write(`[WheelSaver MCP] Fatal: ${e.message}\n`);
  process.exit(1);
});
