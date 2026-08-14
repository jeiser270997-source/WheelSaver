"""
api/llm_providers.py — Configuración de proveedores LLM y handlers de llamada.

Extraído de api/llm.py para mantener responsabilidad única:
- llm_providers.py: catálogo de proveedores free-tier, detección de activos y
  handlers de llamada (OpenAI-compatible, Google Gemini REST, Cohere REST).
- llm.py: orquestación con failover, caché LRU y timeout global.
"""

import json
import os
import re

import httpx
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

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


def get_active_providers():
    """Retorna lista de proveedores configurados (con API key presente)."""
    providers = []

    # OpenAI-compatible con prioridad ascendente (menor número = más prioritario)
    for i, cfg in enumerate(_OPENAI_COMPATIBLE):
        api_key = os.getenv(cfg["env_key"])
        if api_key:
            providers.append(
                {
                    "name": cfg["name"],
                    "api_key": api_key,
                    "base_url": cfg["base_url"],
                    "model": cfg["model"],
                    "priority": i + 1,
                    "type": "openai",
                }
            )

    # Proveedores nativos
    for i, cfg in enumerate(_NATIVE_PROVIDERS):
        api_key = os.getenv(cfg["env_key"])
        if api_key:
            providers.append(
                {
                    "name": cfg["name"],
                    "api_key": api_key,
                    "handler": cfg["handler"],
                    "model": cfg["model"],
                    "priority": len(_OPENAI_COMPATIBLE) + i + 1,
                    "type": "native",
                }
            )

    # Ordenar por prioridad
    providers.sort(key=lambda p: p["priority"])
    return providers


# ──────────────────────────────────────────────────────────────────────────────
# Handlers por tipo de proveedor
# ──────────────────────────────────────────────────────────────────────────────


async def _ask_openai_compatible(provider: dict, system_prompt: str, user_prompt: str, **kwargs) -> str:
    """Consulta a un proveedor con API compatible con OpenAI."""
    client = AsyncOpenAI(
        api_key=provider["api_key"],
        base_url=provider["base_url"],
        timeout=60.0,
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
    """Consulta a Google Gemini API vía REST.

    La API key viaja en el header x-goog-api-key (nunca en la URL) para evitar
    que se filtre por access logs, proxies o referrers (Zero-Leak).
    """
    model = kwargs.get("model", provider["model"])
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    payload = {
        "contents": [{"parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}]}],
        "generationConfig": {
            "maxOutputTokens": kwargs.get("max_tokens", 800),
            "temperature": kwargs.get("temperature", 0.3),
        },
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            url,
            json=payload,
            headers={"x-goog-api-key": provider["api_key"]},
        )
        resp.raise_for_status()
        data = resp.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            # Incluir info de bloqueo de seguridad si existe
            block_reason = data.get("promptFeedback", {}).get("blockReason", "desconocido")
            raise RuntimeError(
                f"Google Gemini: respuesta vacía o bloqueada. blockReason={block_reason}. "
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


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
async def call_handler(handler, provider, system_prompt, user_prompt, **kwargs):
    """Wrapper con retry para cada call individual a un proveedor.
    Separado de ask_llm para que @retry NO envuelva el failover chain completo.
    Sin @lru_cache — no cachear excepciones."""
    return await handler(provider, system_prompt, user_prompt, **kwargs)


def redact_secrets(error_text: str) -> str:
    """Sanitiza errores LLM removiendo API keys de URLs antes de loguear."""
    return re.sub(r"(\?key=|[?&]api_key=)[^&\s\"']+", r"\1[REDACTED]", error_text)
