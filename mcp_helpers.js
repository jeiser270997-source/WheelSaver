/**
 * mcp_helpers.js — Helpers puros del MCP de WheelSaver (testeables sin SDK ni SQLite).
 * Espeja el patrón FTS5 de scraper/search.py (clean_fts_term + OR query + filtros).
 */
'use strict';

const path = require('node:path');

/** Ruta real de la DB (data/top_repos.db en el repo). */
function resolveDbPath(baseDir) {
  return path.join(baseDir, 'data', 'top_repos.db');
}

/** Quita caracteres especiales de operadores FTS5 (igual que clean_fts_term en Python). */
function cleanFtsTerm(term) {
  const special = ['*', '(', ')', ':', '^', '"', '=', String.fromCharCode(92)];
  let t = String(term || '');
  for (const ch of special) {
    t = t.split(ch).join('');
  }
  return t.trim();
}

/** SQL + params para búsqueda FTS5 con filtros (condiciones dinámicas; MATCH nunca dentro de OR). */
function buildSearchQuery(keywords, language, minStars, limit) {
  const terms = (Array.isArray(keywords) ? keywords : [keywords])
    .map((k) => cleanFtsTerm(k))
    .filter((k) => k.length > 0);
  const where = [];
  const params = [];
  if (terms.length > 0) {
    where.push('repos_fts MATCH ?');
    params.push(terms.join(' OR '));
  }
  if (language) {
    where.push('r.language = ?');
    params.push(language);
  }
  if (minStars != null) {
    where.push('r.stars >= ?');
    params.push(minStars);
  }
  params.push(limit);
  const whereSql = where.length > 0 ? 'WHERE ' + where.join(' AND ') : '';
  return {
    sql: `SELECT r.name, r.owner, r.description, r.stars, r.language, r.topics, r.url
          FROM repos_fts f JOIN repos r ON r.rowid = f.rowid
          ${whereSql}
          ORDER BY r.stars DESC LIMIT ?`,
    params,
  };
}

/** SQL + params para top repos por estrellas. */
function buildTopSql(language, limit) {
  return {
    sql: `SELECT name, owner, description, stars, language, topics, url
          FROM repos WHERE (? IS NULL OR language = ?)
          ORDER BY stars DESC LIMIT ?`,
    params: [language || null, language || null, limit],
  };
}

/** SQL + params para stats. */
function buildStatsSql() {
  return {
    sql: `SELECT COUNT(*) AS total, COUNT(DISTINCT language) AS lenguajes,
                 MAX(stars) AS max_stars, ROUND(AVG(stars), 0) AS avg_stars
          FROM repos`,
    params: [],
  };
}

/** SQL + params para lenguajes top. */
function buildLanguagesSql(limit) {
  return {
    sql: `SELECT language, COUNT(*) AS repos FROM repos
          WHERE language IS NOT NULL AND language != ''
          GROUP BY language ORDER BY repos DESC LIMIT ?`,
    params: [limit],
  };
}

/** SQL + params para detalle de un repo por nombre (exacto o LIKE). */
function buildRepoSql(name, limit) {
  return {
    sql: `SELECT name, owner, description, stars, language, topics, url
          FROM repos WHERE name LIKE ? OR owner LIKE ?
          ORDER BY stars DESC LIMIT ?`,
    params: [`%${name}%`, `%${name}%`, limit],
  };
}

function truncate(text, maxLen = 140) {
  if (!text) return '';
  const t = String(text);
  return t.length > maxLen ? `${t.slice(0, maxLen)}...` : t;
}

function formatRepoRows(rows) {
  if (!rows.length) return '';
  return rows.map((r, i) => {
    return `${i + 1}. **${r.name}** (${r.owner}) — ${r.stars}⭐ [${r.language || '?'}]\n   ${truncate(r.description || '')}\n   ${r.url}`;
  }).join('\n\n');
}

function formatStatsRow(row) {
  return `Repos: ${row.total} · Lenguajes: ${row.lenguajes} · Max ⭐: ${row.max_stars} · Promedio ⭐: ${row.avg_stars}`;
}

module.exports = {
  resolveDbPath,
  cleanFtsTerm,
  buildSearchQuery,
  buildTopSql,
  buildStatsSql,
  buildLanguagesSql,
  buildRepoSql,
  truncate,
  formatRepoRows,
  formatStatsRow,
};
