"""scraper/scoring.py — Scoring determinista multi-factor para búsquedas.

Extraído de scraper/search.py para mantener responsabilidad única.
No depende de la BD: calcula el score de un repo contra los términos de búsqueda.
"""

import math
from datetime import datetime


def calculate_repo_score(repo: dict, query_terms: list[str], target_language: str = None) -> float:
    """
    Calcula un score determinista (cero LLM) combinando:
    - Coincidencia exacta en nombre / slug (+15.0 / +8.0)
    - Coincidencia en topics (+3.0)
    - Coincidencia en descripción (+1.0)
    - Peso sublineal de estrellas (log10(stars + 10))
    - Recencia de actualización (factor 0.5x - 1.2x)
    - Boost por lenguaje coincidente (1.5x)
    - Penalización por repo archivado (0.2x)
    """
    name = (repo.get("name") or "").lower()
    owner = (repo.get("owner") or "").lower()
    slug = f"{owner}/{name}"
    desc = (repo.get("description") or "").lower()
    topics_set = {t.strip() for t in (repo.get("topics") or "").lower().split(",") if t.strip()}

    relevance = _score_relevance(name, slug, desc, topics_set, query_terms)
    if relevance == 0.0:
        relevance = 0.5

    star_weight = math.log10(max(repo.get("stars", 0), 1) + 10)
    recency_factor = _score_recency(repo.get("updated_at"))
    lang_factor = _score_language(repo.get("language"), target_language)
    status_factor = 0.2 if repo.get("is_archived") else 1.0

    return round(relevance * star_weight * recency_factor * lang_factor * status_factor, 3)


def _score_relevance(name: str, slug: str, desc: str, topics_set: set, query_terms: list[str]) -> float:
    """Puntuación de relevancia textual (nombre, topics, descripción)."""
    query_str = " ".join(query_terms).lower()
    relevance = 0.0

    if query_str == slug or query_str == name:
        relevance += 15.0
    elif query_str in name:
        relevance += 8.0

    for term in query_terms:
        term_lower = term.lower()
        if term_lower == name:
            relevance += 6.0
        elif term_lower in name:
            relevance += 3.5

        if term_lower in topics_set:
            relevance += 3.0
        elif any(term_lower in t for t in topics_set):
            relevance += 1.5

        if term_lower in desc:
            relevance += 1.0

    return relevance


def _score_recency(updated_at) -> float:
    """Factor de recencia basado en el año de última actualización (0.5x - 1.2x)."""
    if not updated_at:
        return 1.0
    try:
        year = int(updated_at[:4])
        diff = datetime.now().year - year
        if diff <= 0:
            return 1.2
        if diff == 1:
            return 1.0
        if diff == 2:
            return 0.8
        return 0.5
    except Exception:
        return 0.9


def _score_language(repo_lang, target_language: str) -> float:
    """Boost si el lenguaje del repo coincide con el filtro (1.5x), penalización suave si no (0.85x)."""
    if not target_language:
        return 1.0
    repo_lang = (repo_lang or "").lower()
    if repo_lang == target_language.lower():
        return 1.5
    return 0.85
