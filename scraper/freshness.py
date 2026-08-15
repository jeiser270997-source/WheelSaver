"""
scraper/freshness.py — Frescura de la DB (staleness) para actualización reactiva.

WheelSaver es REACTIVO: no hay CI ni jobs programados. La DB se actualiza
cuando se hace un llamado (CLI `update` o MCP). Este módulo decide si la DB
está vieja usando run_history (última corrida completada) con fallback al
mtime del archivo SQLite.
"""

import os
import sqlite3
from datetime import datetime, timezone

from scraper.db_manager import DB_PATH, init_db

# Umbral por defecto: 7 días sin actualizar = DB vieja
DEFAULT_MAX_DAYS = 7


def last_update_time(db_path: str | None = None) -> str | None:
    """ISO timestamp de la última corrida COMPLETADA, o None si nunca."""
    p = db_path or DB_PATH
    if not os.path.exists(p):
        return None
    try:
        conn = sqlite3.connect(p)
        try:
            cur = conn.cursor()
            cur.execute(
                """SELECT finished_at FROM run_history
                   WHERE status = 'completed' AND finished_at IS NOT NULL
                   ORDER BY started_at DESC LIMIT 1"""
            )
            row = cur.fetchone()
        finally:
            conn.close()
        if row and row[0]:
            return row[0]
    except sqlite3.Error:
        pass
    # Fallback: mtime del archivo
    return datetime.fromtimestamp(os.path.getmtime(p), tz=timezone.utc).isoformat()


def staleness_days(db_path: str | None = None) -> int | None:
    """Días (enteros) desde la última actualización. None si no existe la DB."""
    p = db_path or DB_PATH
    if not os.path.exists(p):
        return None
    iso = last_update_time(p)
    if not iso:
        return None
    try:
        last = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - last
        return max(0, int(delta.total_seconds() // 86400))
    except ValueError:
        return None


def is_stale(db_path: str | None = None, max_days: int = DEFAULT_MAX_DAYS) -> bool:
    """True si la DB no existe, nunca se actualizó, o supera max_days."""
    days = staleness_days(db_path)
    if days is None:
        return True  # sin DB o sin registro -> vieja
    return days > max_days


def describe(db_path: str | None = None, max_days: int = DEFAULT_MAX_DAYS) -> str:
    """Descripción legible del estado de frescura."""
    p = db_path or DB_PATH
    if not os.path.exists(p):
        return f"❌ DB no existe en {p}"
    days = staleness_days(p)
    if days is None:
        return "❌ DB sin historial de actualización (corre `wheelsaver update`)"
    if is_stale(p, max_days):
        return f"⚠️ DB desactualizada ({days}d > {max_days}d) — corre `wheelsaver update`"
    return f"✅ DB fresca (última actualización hace {days}d)"


__all__ = ["last_update_time", "staleness_days", "is_stale", "describe", "DEFAULT_MAX_DAYS"]
