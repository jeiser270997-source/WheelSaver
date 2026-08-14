"""scraper/synonyms.py — Diccionario offline de sinónimos técnicos y expansión de keywords."""

SYNONYM_MAP = {
    "autenticacion": ["auth", "jwt", "oauth"],
    "autenticación": ["auth", "jwt", "oauth"],
    "seguridad": ["security", "audit", "encryption"],
    "bd": ["database", "orm", "sql"],
    "graficos": ["chart", "visualization", "plotting"],
    "gráficos": ["chart", "visualization", "plotting"],
    "monitoreo": ["monitoring", "metrics", "telemetry"],
    "cola": ["queue", "broker", "celery"],
    "colas": ["queue", "broker", "celery"],
    "pdf": ["pdf", "pdf-parser"],
    "imagenes": ["image", "image-processing"],
    "imágenes": ["image", "image-processing"],
}


def expand_keywords_offline(keywords: list[str]) -> list[str]:
    """Expande keywords usando un diccionario offline de sinónimos técnicos."""
    expanded = list(keywords)
    for kw in keywords:
        clean_kw = kw.lower().strip()
        if clean_kw in SYNONYM_MAP:
            for syn in SYNONYM_MAP[clean_kw]:
                if syn not in expanded:
                    expanded.append(syn)
    return expanded
