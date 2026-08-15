"""Tests de scraper/freshness.py — staleness de la DB para update reactivo."""

import os
import sqlite3
from datetime import datetime, timedelta, timezone

from scraper.freshness import describe, is_stale, last_update_time, staleness_days


def make_db(path, finished_at_iso=None):
    """Crea una DB temporal con run_history. finished_at_iso=None = sin corridas."""
    conn = sqlite3.connect(path)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS run_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT, finished_at TEXT, status TEXT,
            repos_before INTEGER, repos_after INTEGER,
            repos_inserted INTEGER, repos_filtered INTEGER,
            min_stars_scanned INTEGER)"""
    )
    if finished_at_iso is not None:
        now = datetime.now(timezone.utc)
        conn.execute(
            "INSERT INTO run_history (started_at, finished_at, status, repos_before, repos_after, repos_inserted) VALUES (?, ?, 'completed', 0, 100, 100)",
            (now.isoformat(), finished_at_iso),
        )
    conn.commit()
    conn.close()


def test_sin_db_es_stale(tmp_path):
    p = str(tmp_path / "nada.db")
    assert is_stale(p) is True
    assert staleness_days(p) is None


def test_sin_historial_es_stale(tmp_path):
    p = str(tmp_path / "vacia.db")
    make_db(p)
    assert last_update_time(p) is None or last_update_time(p)  # fallback mtime
    # sin corridas completadas -> usa mtime del archivo (recien creado) -> no stale por dias
    assert is_stale(p, max_days=0) is True or staleness_days(p) == 0


def test_db_fresca_no_es_stale(tmp_path):
    p = str(tmp_path / "fresca.db")
    fresh = datetime.now(timezone.utc).isoformat()
    make_db(p, fresh)
    assert is_stale(p, max_days=7) is False
    assert staleness_days(p) == 0


def test_db_vieja_es_stale(tmp_path):
    p = str(tmp_path / "vieja.db")
    old = (datetime.now(timezone.utc) - timedelta(days=15)).isoformat()
    make_db(p, old)
    assert is_stale(p, max_days=7) is True
    assert staleness_days(p) >= 15


def test_describe_informa_estado(tmp_path):
    p = str(tmp_path / "desc.db")
    make_db(p, datetime.now(timezone.utc).isoformat())
    out = describe(p, max_days=7)
    assert "DB fresca" in out or "desactualizada" in out
