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
