'use strict';
const test = require('node:test');
const assert = require('node:assert');
const path = require('node:path');
const H = require('../mcp_helpers.js');

test('resolveDbPath apunta a data/top_repos.db', () => {
  const p = H.resolveDbPath('C:/x/WHEELSAVER');
  assert.ok(p.endsWith(path.join('data', 'top_repos.db')));
});

test('cleanFtsTerm quita operadores FTS5', () => {
  assert.strictEqual(H.cleanFtsTerm('fastapi*'), 'fastapi');
  assert.strictEqual(H.cleanFtsTerm('(pdf)'), 'pdf');
  assert.strictEqual(H.cleanFtsTerm('voice:clone'), 'voiceclone');
  assert.strictEqual(H.cleanFtsTerm(''), '');
});

test('buildSearchQuery: MATCH directo (no en OR) con términos limpios', () => {
  const q = H.buildSearchQuery(['tts', 'voice'], 'Python', 1000, 5);
  assert.ok(q.sql.includes('repos_fts MATCH ?'));
  assert.ok(!q.sql.includes('IS NULL OR'));
  assert.ok(q.params.includes('tts OR voice'));
  assert.strictEqual(q.params[q.params.length - 1], 5);
});

test('buildSearchQuery: sin filtros opcionales no agrega condiciones', () => {
  const q = H.buildSearchQuery(['pdf'], null, null, 3);
  assert.strictEqual(q.params.length, 2);
  assert.ok(q.params[0] === 'pdf');
});

test('buildSearchQuery: sin términos válidos devuelve query sin WHERE', () => {
  const q = H.buildSearchQuery(['*', '(', ')'], null, null, 10);
  assert.ok(!q.sql.includes('MATCH'));
  assert.strictEqual(q.params.length, 1);
});

test('buildTopSql filtra por lenguaje opcional', () => {
  const q = H.buildTopSql('Rust', 5);
  assert.ok(q.sql.includes('language = ?'));
  assert.ok(q.sql.includes('ORDER BY stars DESC'));
});

test('buildStatsSql calcula total, lenguajes, max y avg', () => {
  const q = H.buildStatsSql();
  assert.ok(q.sql.includes('COUNT(*) AS total'));
  assert.ok(q.sql.includes('AVG(stars)'));
});

test('buildLanguagesSql agrupa por lenguaje', () => {
  const q = H.buildLanguagesSql(10);
  assert.ok(q.sql.includes('GROUP BY language'));
});

test('buildRepoSql busca por name y owner', () => {
  const q = H.buildRepoSql('coqui', 3);
  assert.strictEqual(q.params[0], '%coqui%');
  assert.strictEqual(q.params[1], '%coqui%');
});

test('truncate corta largo y respeta corto', () => {
  assert.strictEqual(H.truncate('abc'), 'abc');
  assert.ok(H.truncate('x'.repeat(300)).endsWith('...'));
});

test('formatRepoRows formatea con estrellas y lenguaje', () => {
  const rows = [{ name: 'TTS', owner: 'coqui-ai', description: 'toolkit', stars: 45714, language: 'Python', url: 'https://github.com/coqui-ai/TTS' }];
  const out = H.formatRepoRows(rows);
  assert.ok(out.includes('TTS'));
  assert.ok(out.includes('45714⭐'));
  assert.ok(out.includes('[Python]'));
});

test('formatRepoRows vacío devuelve vacío', () => {
  assert.strictEqual(H.formatRepoRows([]), '');
});

test('stalenessInfo: DB fresca (run_history reciente) -> isStale false', () => {
  const now = Date.now();
  const dbStub = { prepare: () => ({ get: () => ({ finished_at: new Date(now).toISOString() }) }) };
  const info = H.stalenessInfo(dbStub, 7);
  assert.strictEqual(info.isStale, false);
  assert.strictEqual(info.days, 0);
  assert.ok(H.stalenessNote(info).includes('DB fresca'));
});

test('stalenessInfo: DB vieja (15d) -> isStale true y nota de aviso', () => {
  const old = new Date(Date.now() - 15 * 86400000).toISOString();
  const dbStub = { prepare: () => ({ get: () => ({ finished_at: old }) }) };
  const info = H.stalenessInfo(dbStub, 7);
  assert.strictEqual(info.isStale, true);
  assert.ok(info.days >= 15);
  assert.ok(H.stalenessNote(info).includes('wheelsaver_update'));
});

test('stalenessInfo: sin run_history -> isStale true (sin historial)', () => {
  const dbStub = { prepare: () => ({ get: () => undefined }) };
  const info = H.stalenessInfo(dbStub, 7);
  assert.strictEqual(info.isStale, true);
  assert.strictEqual(info.days, null);
});

test('stalenessInfo: error de query -> isStale true sin romper', () => {
  const dbStub = { prepare: () => { throw new Error('boom'); } };
  const info = H.stalenessInfo(dbStub, 7);
  assert.strictEqual(info.isStale, true);
});

test('stalenessNote: sin info devuelve vacio', () => {
  assert.strictEqual(H.stalenessNote(null), '');
});
