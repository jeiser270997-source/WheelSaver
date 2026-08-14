"""cli_ui.py — Helpers compartidos de UI para los comandos CLI.

Console y clean() se usan desde cli.py y cli_commands/*. Se aíslan aquí
para evitar imports circulares entre módulos.
"""

import re

from rich.console import Console

console = Console()


def clean(text, max_len=80):
    """Sanitizador para Windows cp1252 — limpia emojis y no-ASCII."""
    if not text:
        return ""
    # Remueve todo lo que no sea ASCII imprimible (+ acentos comunes)
    cleaned = re.sub(r"[^\x20-\x7EÀ-ÿĀ-ſ]", "", text)
    return cleaned[:max_len] + "..." if len(cleaned) > max_len else cleaned
