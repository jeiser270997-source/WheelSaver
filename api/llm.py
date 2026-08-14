"""
WheelSaver LLM — Orquestación multi-proveedor con failover automático.

Este módulo orquesta la llamada al mejor LLM disponible con:
- Failover automático entre proveedores free tier (ver api/llm_providers.py).
- Timeout global de 45s.
- Caché LRU de respuestas (máx. 500 entradas).
- Modo offline cuando no hay proveedores configurados.

Para agregar un nuevo proveedor: edita api/llm_providers.py.
"""

import asyncio
from collections import OrderedDict

from api.audit_reports import build_offline_audit_report, build_static_analysis_summary
from api.llm_providers import (
    _NATIVE_HANDLERS,
    _OPENAI_HANDLERS,
    call_handler,
    redact_secrets,
)
from api.llm_providers import (
    get_active_providers as _get_active_providers,
)

# Alias de compatibilidad (los tests parchean api.llm._get_active_providers)
# noqa: F401 — se re-exporta intencionalmente
__all__ = [
    "_get_active_providers",
    "ask_llm",
    "ask_llm_about_repos",
    "expand_search_query",
    "generate_skill_from_repo",
    "audit_project_with_ai",
]


def _build_prompts(question: str, repos: list[dict]) -> tuple[str, str]:
    """Construye system_prompt y user_prompt para consulta RAG."""
    context = ""
    for r in repos:
        desc = r.get("description", "Sin descripción") or "Sin descripción"
        lang = r.get("language", "-") or "-"
        context += f"- {r['owner']}/{r['name']} ({r.get('stars', 0)}⭐): {desc}. Lenguaje: {lang}\n"

    if not context:
        context = "No se encontraron repositorios relevantes en la base de datos."

    system_prompt = (
        "Eres WheelSaver AI, un ingeniero de software senior altamente experimentado.\n"
        "Tu objetivo es analizar la pregunta del usuario y responder recomendando los "
        "mejores repositorios basándote estrictamente en el contexto proporcionado "
        "(los resultados de la base de datos local).\n"
        "Sé directo, explica brevemente por qué recomiendas una librería sobre otra, "
        "y usa un formato Markdown limpio."
    )

    user_prompt = f"""Pregunta del usuario: "{question}"

Contexto extraído de la base de datos de WheelSaver:
{context}

Por favor, analiza estos repositorios y responde a la pregunta de la mejor manera posible."""

    return system_prompt, user_prompt


_RESPONSE_CACHE: OrderedDict[tuple, str] = OrderedDict()
_RESPONSE_CACHE_MAX = 500


async def _ask_llm_internal(system_prompt: str = "", user_prompt: str = "", **kwargs) -> str:
    cache_key = (system_prompt, user_prompt)
    if cache_key in _RESPONSE_CACHE:
        _RESPONSE_CACHE.move_to_end(cache_key)
        return _RESPONSE_CACHE[cache_key]

    providers = _get_active_providers()
    if not providers:
        raise RuntimeError(
            "No hay proveedores LLM configurados. "
            "Revisa tu archivo .env — necesitas al menos una API key "
            "(GROQ_API_KEY, CEREBRAS_API_KEY, GOOGLE_API_KEY, etc.)"
        )

    errors = []
    for provider in providers:
        try:
            if provider["type"] == "openai":
                handler = _OPENAI_HANDLERS.get(provider["name"], _ask_openai_compatible_fallback)
                res = await call_handler(handler, provider, system_prompt, user_prompt, **kwargs)
                _cache_response(cache_key, res)
                return res
            else:  # native
                handler = _NATIVE_HANDLERS.get(provider["name"])
                if handler:
                    res = await call_handler(handler, provider, system_prompt, user_prompt, **kwargs)
                    _cache_response(cache_key, res)
                    return res
                errors.append(f"{provider['name']}: handler desconocido")
                continue
        except Exception as e:
            clean_err = redact_secrets(str(e))
            err_msg = f"{provider['name']} ({provider.get('model', '?')}): {clean_err}"
            errors.append(err_msg)
            continue

    raise RuntimeError("Todos los proveedores LLM fallaron.\n" + "\n".join(f"  - {e}" for e in errors))


async def _ask_openai_compatible_fallback(provider, system_prompt, user_prompt, **kwargs):
    """Handler por defecto si el nombre del proveedor no está mapeado."""
    from api.llm_providers import _ask_openai_compatible

    return await _ask_openai_compatible(provider, system_prompt, user_prompt, **kwargs)


def _cache_response(cache_key: tuple, res: str) -> None:
    """Guarda una respuesta en la caché LRU, respetando el tamaño máximo."""
    _RESPONSE_CACHE[cache_key] = res
    if len(_RESPONSE_CACHE) > _RESPONSE_CACHE_MAX:
        _RESPONSE_CACHE.popitem(last=False)


async def ask_llm(system_prompt: str = "", user_prompt: str = "", **kwargs) -> str:
    """Wrapper principal con timeout global de 45s."""
    try:
        return await asyncio.wait_for(_ask_llm_internal(system_prompt, user_prompt, **kwargs), timeout=45.0)
    except asyncio.TimeoutError:
        raise RuntimeError("Timeout global superado (45s) en la consulta multi-proveedor LLM.")


async def ask_llm_about_repos(question: str, repos: list[dict], **kwargs) -> str:
    """
    Toma una pregunta del usuario y una lista de repositorios (obtenidos de la DB local),
    y usa el mejor LLM disponible para razonar y dar una respuesta experta.

    Args:
        question: Pregunta del usuario sobre repositorios/librerías.
        repos: Lista de diccionarios con datos de repositorios.
        **kwargs: Parámetros adicionales para el LLM (max_tokens, temperature).

    Returns:
        Respuesta en Markdown del LLM.
    """
    system_prompt, user_prompt = _build_prompts(question, repos)

    try:
        return await ask_llm(system_prompt=system_prompt, user_prompt=user_prompt, **kwargs)
    except RuntimeError as e:
        return f"Error al generar respuesta: {e}"


async def expand_search_query(question: str) -> list[str]:
    """
    Toma una pregunta natural del usuario y usa el LLM para extraer keywords
    técnicas exactas que puedan coincidir en GitHub.
    """
    sys_prompt = (
        "Eres un experto en GitHub. El usuario hará una pregunta en lenguaje natural. "
        "Extrae 3 a 6 keywords o tags técnicos exactos (en inglés) que un repositorio de GitHub "
        "para este propósito usaría. Responde SÓLO con las palabras clave separadas por comas. "
        "No des explicaciones."
    )

    try:
        # Usamos temperature=0.0 para consistencia
        resp = await ask_llm(system_prompt=sys_prompt, user_prompt=question, temperature=0.0)
        # Limpiar la respuesta (quitar puntos finales, saltos de línea, etc.)
        cleaned = resp.replace(".", "").replace("\n", "").strip()
        keywords = [k.strip() for k in cleaned.split(",") if k.strip()]
        return keywords if keywords else question.split()
    except Exception:
        # Fallback a split basico
        return [kw.strip() for kw in question.replace("?", "").replace("¿", "").split() if len(kw) > 3]


async def generate_skill_from_repo(repo_name: str, description: str, readme: str) -> str:
    """
    Genera un archivo SKILL.md de Antigravity (Agente de IA) basado en el repo.
    """
    sys_prompt = (
        "Eres un ingeniero de IA creando un 'Skill' para otro agente autónomo de IA (Antigravity). "
        "El agente necesita saber cómo usar este repositorio de GitHub en el proyecto del usuario. "
        "Genera el contenido de un archivo SKILL.md."
    )

    # Recortar el readme si es demasiado grande para evitar exceder tokens
    # Truncar en boundary de linea mas cercana a 15k, no char-count duro
    if readme:
        if len(readme) > 15000:
            readme_snippet = readme[: readme.rfind("\n", 0, 15000)] if "\n" in readme[:15000] else readme[:15000]
        else:
            readme_snippet = readme
    else:
        readme_snippet = "Sin README"

    user_prompt = f"""
Basado en el repositorio {repo_name}, genera un SKILL.md.
Descripción: {description}
README:
{readme_snippet}

REGLAS DEL SKILL.MD:
1. DEBE comenzar con frontmatter YAML (name: NombreSkill, description: Breve descripción de qué hace).
2. Luego un título markdown #.
3. Secciones útiles para una IA: ¿Cuándo usarlo?, ¿Cómo integrarlo?, Comandos útiles, Ejemplos de código, y "Gotchas" (errores comunes).
4. Escribe directamente el contenido, sin usar bloques de código envolventes markdown grandes ```markdown, solo el contenido puro.
"""
    try:
        resp = await ask_llm(system_prompt=sys_prompt, user_prompt=user_prompt, temperature=0.3)
        if not resp.startswith("---"):
            resp = f"---\n{resp.lstrip()}"
            if "\n#" in resp and "\n---\n#" not in resp:
                resp = resp.replace("\n#", "\n---\n#", 1)
        return resp
    except Exception as e:
        return f"---\nname: Skill Error\ndescription: Falló la generacion\n---\nError: {e}"


_build_static_analysis_summary = build_static_analysis_summary
_build_offline_audit_report = build_offline_audit_report


async def audit_project_with_ai(audit_data: dict, missing_categories: list, static_analysis: dict = None, **kwargs) -> str:
    """
    Realiza una auditoría profunda de la arquitectura y el estado del proyecto local.
    Si todo esta perfecto (missing_categories está vacío), devuelve el badge oficial.
    """
    if not missing_categories and not static_analysis:
        return (
            "✅ **APROBADO POR WHEELSAVER**\n\n"
            "Tu proyecto cumple con todos los estándares, está blindado y sin deuda técnica. "
            "¡Puedes cerrar el proyecto o lanzarlo a producción con total confianza!"
        )

    sys_prompt = (
        "Eres un arquitecto de software experto (WheelSaver AI Auditor). "
        "Se te pasará el análisis de un proyecto de código. Debes dar un diagnóstico breve "
        "y brutalmente honesto, indicando por qué les faltan ciertas cosas, qué problemas "
        "de seguridad o calidad de código existen, y cómo arreglarlo rápido."
    )

    missing_str = "\n".join([f"- {label} (Categoria: {cat})" for label, cat, _ in missing_categories]) if missing_categories else ""
    static_str = _build_static_analysis_summary(static_analysis)

    user_prompt = f"""He auditado este proyecto localmente.
Stack: {audit_data["stack_str"]}
Framework: {audit_data["framework"]}

Faltan los siguientes componentes críticos:
{missing_str if missing_str else "(Ninguno — todos los checks básicos están cubiertos)"}
{static_str}

Dame un informe de Auditoría Profunda indicando el impacto de los hallazgos y un consejo directo.
"""
    if not _get_active_providers():
        return _build_offline_audit_report(audit_data, missing_categories, static_analysis)

    try:
        return await ask_llm(system_prompt=sys_prompt, user_prompt=user_prompt, temperature=0.3)
    except Exception as e:
        return f"Error en la auditoría AI: {e}"
