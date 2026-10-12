"""Local LLM providers (Ollama, LM Studio): discovery and non-streaming chat.

Both are probed on the default ports (override with OLLAMA_URL / LMSTUDIO_URL). Embedding
models are filtered out of the chat model lists; loaded models are listed first.
"""

import os
import re
from typing import Any

import httpx

from .logging_config import get_logger

logger = get_logger("directmedia_mcp.llm")

PROVIDERS = {
    "ollama": os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"),
    "lmstudio": os.getenv("LMSTUDIO_URL", "http://127.0.0.1:1234"),
}
_THINK = re.compile(r"<think>.*?</think>\s*", re.DOTALL)


def _is_embedding(model_id: str, kind: str | None = None) -> bool:
    return kind == "embeddings" or "embed" in model_id.lower()


async def list_providers(timeout: float = 3.0) -> list[dict[str, Any]]:
    """[{name, url, available, models}] for every known provider; never raises."""
    out = []
    async with httpx.AsyncClient(timeout=timeout) as client:
        for name, url in PROVIDERS.items():
            models: list[str] = []
            available = False
            try:
                if name == "ollama":
                    resp = await client.get(f"{url}/api/tags")
                    resp.raise_for_status()
                    models = [m["name"] for m in resp.json().get("models", []) if not _is_embedding(m["name"])]
                else:
                    resp = await client.get(f"{url}/api/v0/models")
                    if resp.status_code == 404:  # older LM Studio: OpenAI listing only
                        resp = await client.get(f"{url}/v1/models")
                    resp.raise_for_status()
                    rows = [r for r in resp.json().get("data", []) if not _is_embedding(r["id"], r.get("type"))]
                    rows.sort(key=lambda r: r.get("state") != "loaded")
                    models = [r["id"] for r in rows]
                available = True
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                logger.debug("provider %s unavailable: %s", name, exc)
            out.append({"name": name, "url": url, "available": available, "models": models})
    return out


async def chat(provider: str, model: str, messages: list[dict[str, str]], timeout: float = 600.0) -> str:
    """One chat completion. LM Studio may load the model on first use, hence the long timeout."""
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown provider {provider!r}; expected one of {sorted(PROVIDERS)}")
    url = PROVIDERS[provider]
    async with httpx.AsyncClient(timeout=timeout) as client:
        if provider == "ollama":
            resp = await client.post(f"{url}/api/chat", json={"model": model, "messages": messages, "stream": False})
            resp.raise_for_status()
            text = resp.json()["message"]["content"]
        else:
            body = {"model": model, "messages": messages, "temperature": 0.3, "stream": False}
            resp = await client.post(f"{url}/v1/chat/completions", json=body)
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"]
    return _THINK.sub("", text or "").strip()
