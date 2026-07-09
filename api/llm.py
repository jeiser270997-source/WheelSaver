"""
WheelSaver LLM — Proveedor multi-LLM con fallback automático.

Soporta múltiples proveedores free tier (OpenAI-compatible + Google Gemini + Cohere)
y hace failover automático si uno falla (rate limit, timeout, etc.).

Para agregar un nuevo proveedor:
  1. Agrega su config en _OPENAI_COMPATIBLE o _NATIVE_PROVIDERS
  2. Implementa su handler en _ask_* (si no es OpenAI-compatible)
  3. Agrega la API key al .env
"""

import os
import json
import httpx
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────────────────────────────────────────────
# Configuración de proveedores
# ──────────────────────────────────────────────────────────────────────────────

# Proveedores con API compatible con OpenAI (reusan AsyncOpenAI)
_OPENAI_COMPATIBLE = [
    {
        "name": "groq",
        "env_key": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
    },
    {
        "name": "cerebras",
        "env_key": "CEREBRAS_API_KEY",
        "base_url": "https://api.cerebras.ai/v1",
        "model": "llama-3.3-70b",
    },
    {
        "name": "openrouter",
        "env_key": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "google/gemini-2.0-flash-exp:free",
    },
    {
        "name": "nvidia",
        "env_key": "NVIDIA_API_KEY",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "model": "meta/llama-3.1-70b-instruct",
    },
    {
        "name": "sambanova",
        "env_key": "SAMBANOVA_API_KEY",
        "base_url": "https://api.sambanova.ai/v1",
        "model": "Meta-Llama-3.1-70B-Instruct",
    },
    {
        "name": "mistral",
        "env_key": "MISTRAL_API_KEY",
        "base_url": "https://api.mistral.ai/v1",
        "model": "mistral-small-latest",
    },
    {
        "name": "huggingface",
        "env_key": "HF_API_KEY",
        "base_url": "https://api-inference.huggingface.co/v1/",
        "model": "meta-llama/Llama-3.1-70B-Instruct",
    },
]

# Proveedores con API nativa (no OpenAI-compatible)
_NATIVE_PROVIDERS = [
    {
        "name": "google",
        "env_key": "GOOGLE_API_KEY",
        "handler": "_ask_google",
        "model": "gemini-1.5-flash",
    },
    {
        "name": "google-2",
        "env_key": "GOOGLE_API_KEY_2",
        "handler": "_ask_google",
        "model": "gemini-1.5-flash",
    },
    {
        "name": "cohere",
        "env_key": "COHERE_API_KEY",
        "handler": "_ask_cohere",
        "model": "command-r-plus",
    },
]


def _get_active_providers():
    """Retorna lista de proveedores configurados (con API key presente)."""
    providers = []

    # OpenAI-compatible con prioridad ascendente (menor número = más prioritario)
    for i, cfg in enumerate(_OPENAI_COMPATIBLE):
        api_key = os.getenv(cfg["env_key"])
        if api_key:
            providers.append({
                "name": cfg["name"],
                "api_key": api_key,
                "base_url": cfg["base_url"],
                "model": cfg["model"],
                "priority": i + 1,
                "type": "openai",
            })

    # Proveedores nativos
    for i, cfg in enumerate(_NATIVE_PROVIDERS):
        api_key = os.getenv(cfg["env_key"])
        if api_key:
            providers.append({
                "name": cfg["name"],
                "api_key": api_key,
                "handler": cfg["handler"],
                "model": cfg["model"],
                "priority": len(_OPENAI_COMPATIBLE) + i + 1,
                "type": "native",
            })

    # Ordenar por prioridad
    providers.sort(key=lambda p: p["priority"])
    return providers


def _build_prompts(question: str, repos: list[dict]) -> tuple[str, str]:
    """Construye system_prompt y user_prompt para consulta RAG."""
    context = ""
    for r in repos:
        desc = r.get("description", "Sin descripción") or "Sin descripción"
        lang = r.get("language", "-") or "-"
        context += f"- {r['owner']}/{r['name']} ({r.get('stars', 0)}⭐): {desc}. Lenguaje: {lang}\n"

    if not context:
        context = "No se encontraron repositorios relevantes en la base de datos."

    system_prompt = """Eres WheelSaver AI, un ingeniero de software senior altamente experimentado.
Tu objetivo es analizar la pregunta del usuario y responder recomendando los mejores repositorios basándote estrictamente en el contexto proporcionado (los resultados de la base de datos local).
Sé directo, explica brevemente por qué recomiendas una librería sobre otra, y usa un formato Markdown limpio."""

    user_prompt = f"""Pregunta del usuario: "{question}"

Contexto extraído de la base de datos de WheelSaver:
{context}

Por favor, analiza estos repositorios y responde a la pregunta de la mejor manera posible."""

    return system_prompt, user_prompt


# ──────────────────────────────────────────────────────────────────────────────
# Handlers por tipo de proveedor
# ──────────────────────────────────────────────────────────────────────────────

async def _ask_openai_compatible(provider: dict, system_prompt: str, user_prompt: str, **kwargs) -> str:
    """Consulta a un proveedor con API compatible con OpenAI."""
    client = AsyncOpenAI(
        api_key=provider["api_key"],
        base_url=provider["base_url"],
    )
    response = await client.chat.completions.create(
        model=provider["model"],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=kwargs.get("max_tokens", 800),
        temperature=kwargs.get("temperature", 0.3),
    )
    return response.choices[0].message.content


async def _ask_google(provider: dict, system_prompt: str, user_prompt: str, **kwargs) -> str:
    """Consulta a Google Gemini API vía REST."""
    model = kwargs.get("model", provider["model"])
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
        f":generateContent?key={provider['api_key']}"
    )

    payload = {
        "contents": [{"parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}]}],
        "generationConfig": {
            "maxOutputTokens": kwargs.get("max_tokens", 800),
            "temperature": kwargs.get("temperature", 0.3),
        },
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            # Incluir info de bloqueo de seguridad si existe
            block_reason = data.get("promptFeedback", {}).get("blockReason", "desconocido")
            raise RuntimeError(
                f"Google Gemini: respuesta vacía o bloqueada. "
                f"blockReason={block_reason}. "
                f"Respuesta completa: {json.dumps(data, indent=2)[:500]}"
            ) from e


async def _ask_cohere(provider: dict, system_prompt: str, user_prompt: str, **kwargs) -> str:
    """Consulta a Cohere API vía REST."""
    model = kwargs.get("model", provider["model"])
    url = "https://api.cohere.ai/v1/chat"

    payload = {
        "model": model,
        "message": user_prompt,
        "preamble": system_prompt,
        "max_tokens": kwargs.get("max_tokens", 800),
        "temperature": kwargs.get("temperature", 0.3),
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {provider['api_key']}"},
        )
        resp.raise_for_status()
        data = resp.json()
        return data["text"]


# ──────────────────────────────────────────────────────────────────────────────
# Handler router
# ──────────────────────────────────────────────────────────────────────────────

_OPENAI_HANDLERS = {
    "groq": _ask_openai_compatible,
    "cerebras": _ask_openai_compatible,
    "openrouter": _ask_openai_compatible,
    "nvidia": _ask_openai_compatible,
    "sambanova": _ask_openai_compatible,
    "mistral": _ask_openai_compatible,
    "huggingface": _ask_openai_compatible,
}

_NATIVE_HANDLERS = {
    "google": _ask_google,
    "google-2": _ask_google,
    "cohere": _ask_cohere,
}


async def ask_llm(system_prompt: str = "", user_prompt: str = "", **kwargs) -> str:
    """
    Consulta al mejor LLM disponible entre los proveedores configurados.
    Hace failover automático: si el primero falla, prueba el siguiente.

    Args:
        system_prompt: Instrucciones de sistema para el modelo.
        user_prompt: Pregunta o instrucción del usuario.
        **kwargs: max_tokens, temperature, etc.

    Returns:
        Respuesta del primer proveedor que responda exitosamente.

    Raises:
        RuntimeError: Si todos los proveedores fallan.
    """
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
                handler = _OPENAI_HANDLERS.get(provider["name"], _ask_openai_compatible)
                return await handler(provider, system_prompt, user_prompt, **kwargs)
            else:  # native
                handler = _NATIVE_HANDLERS.get(provider["name"])
                if handler:
                    return await handler(provider, system_prompt, user_prompt, **kwargs)
                else:
                    errors.append(f"{provider['name']}: handler desconocido")
                    continue
        except Exception as e:
            err_msg = f"{provider['name']} ({provider.get('model', '?')}): {e}"
            errors.append(err_msg)
            continue

    raise RuntimeError(
        "Todos los proveedores LLM fallaron.\n" + "\n".join(f"  - {e}" for e in errors)
    )


# ──────────────────────────────────────────────────────────────────────────────
# Función principal para RAG (backwards compatible + mejorada)
# ──────────────────────────────────────────────────────────────────────────────

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


# ─── Alias backwards-compatible ───────────────────────────────────────────────
ask_deepseek_about_repos = ask_llm_about_repos
