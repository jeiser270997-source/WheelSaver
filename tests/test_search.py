"""
Tests de busqueda para WheelSaver.

Cubre: busqueda por keyword exacta, parcial, multi-keyword,
sin resultados, y caracteres especiales.
"""

import sqlite3
import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestSearch:
    """Tests de busqueda usando la BD in-memory de conftest."""

    def test_search_exact_name(self, db_with_data):
        """Buscar por nombre exacto debe encontrar el repo."""
        cursor = db_with_data.cursor()
        cursor.execute(
            """SELECT r.name, r.owner, r.description, r.url, r.stars, r.language, r.topics
               FROM repos_fts f JOIN repos r ON r.rowid = f.rowid
               WHERE repos_fts MATCH ? ORDER BY r.stars DESC""",
            ("fastapi",),
        )
        results = cursor.fetchall()
        names = [r[0] for r in results]
        assert "fastapi" in names

    def test_search_partial_name(self, db_with_data):
        """Buscar por parte del nombre debe encontrar coincidencias."""
        cursor = db_with_data.cursor()
        like_kw = "%code%"
        cursor.execute(
            """SELECT name, description FROM repos
               WHERE name LIKE ? OR description LIKE ?
               ORDER BY stars DESC LIMIT 5""",
            (like_kw, like_kw),
        )
        results = cursor.fetchall()
        assert len(results) >= 1
        # vscode tiene "Visual Studio Code" en descripcion
        descriptions = [r[1].lower() for r in results]
        names = [r[0].lower() for r in results]
        assert any("code" in d for d in descriptions) or any("code" in n for n in names)

    def test_search_multi_keyword(self, db_with_data):
        """Busqueda multi-keyword con OR."""
        cursor = db_with_data.cursor()
        fts_query = "fastapi OR flask"
        cursor.execute(
            """SELECT DISTINCT r.name, r.stars
               FROM repos_fts f JOIN repos r ON r.rowid = f.rowid
               WHERE repos_fts MATCH ?
               ORDER BY r.stars DESC""",
            (fts_query,),
        )
        results = cursor.fetchall()
        names = [r[0] for r in results]
        assert "fastapi" in names
        assert "flask" in names

    def test_search_no_results(self, db_with_data):
        """Busqueda sin resultados debe retornar lista vacia."""
        cursor = db_with_data.cursor()
        cursor.execute(
            """SELECT r.name FROM repos_fts f JOIN repos r ON r.rowid = f.rowid
               WHERE repos_fts MATCH ?""",
            ("zzzznonexistent12345xxxxx",),
        )
        assert cursor.fetchall() == []

    def test_search_by_language(self, db_with_data):
        """Filtrar por lenguaje debe devolver solo repos de ese lenguaje."""
        cursor = db_with_data.cursor()
        cursor.execute(
            "SELECT name, language FROM repos WHERE language = ? ORDER BY stars DESC",
            ("Python",),
        )
        results = cursor.fetchall()
        assert len(results) == 3  # fastapi, flask, tensorflow
        for r in results:
            assert r[1] == "Python"

    def test_search_by_stars_range(self, db_with_data):
        """Filtrar por rango de estrellas funciona."""
        cursor = db_with_data.cursor()
        cursor.execute(
            "SELECT name, stars FROM repos WHERE stars >= 100000 ORDER BY stars DESC",
        )
        results = cursor.fetchall()
        assert len(results) >= 2  # tensorflow (190k) y vscode (175k) o rust (102k)
        for r in results:
            assert r[1] >= 100000

    def test_search_by_owner(self, db_with_data):
        """Filtrar por owner debe devolver solo repos de ese owner."""
        cursor = db_with_data.cursor()
        cursor.execute(
            "SELECT name, owner FROM repos WHERE owner = ?",
            ("microsoft",),
        )
        results = cursor.fetchall()
        assert len(results) == 1
        assert results[0][0] == "vscode"

    def test_search_order_by_stars(self, db_with_data):
        """Resultados deben estar ordenados por estrellas descendente."""
        cursor = db_with_data.cursor()
        cursor.execute(
            "SELECT name, stars FROM repos ORDER BY stars DESC",
        )
        results = cursor.fetchall()
        stars = [r[1] for r in results]
        assert stars == sorted(stars, reverse=True)
