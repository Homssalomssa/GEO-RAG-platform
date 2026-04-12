"""
LLM Service — Gemma 3 4B via Ollama.

Handles all text generation. Takes a fully constructed prompt
and returns the model's response. No prompt building here —
that's prompt_builder.py's job.
"""

import httpx
import logging

from config import OLLAMA_BASE_URL, LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS, OLLAMA_TIMEOUT

logger = logging.getLogger(__name__)


async def generate(prompt: str, temperature: float = None, max_tokens: int = None) -> str:
    """
    Send a prompt to Gemma 3 via Ollama and return the generated text.

    Args:
        prompt: Fully constructed prompt (from prompt_builder)
        temperature: Override default temperature (optional)
        max_tokens: Override default max tokens (optional)

    Returns:
        Generated text string

    Raises:
        ConnectionError: If Ollama is unreachable
        RuntimeError: If generation fails or returns empty
    """
    payload = {
        "model": LLM_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature or LLM_TEMPERATURE,
            "num_predict": max_tokens or LLM_MAX_TOKENS,
        }
    }

    async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
        try:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json=payload
            )
            response.raise_for_status()
        except httpx.ConnectError:
            raise ConnectionError(f"Cannot connect to Ollama at {OLLAMA_BASE_URL}")
        except httpx.HTTPStatusError as e:
            raise ConnectionError(f"Ollama returned error: {e.response.status_code}")

    result = response.json().get("response", "").strip()

    if not result:
        # Retry once — Ollama occasionally returns empty
        logger.warning("Empty LLM response, retrying once...")
        try:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json=payload
            )
            result = response.json().get("response", "").strip()
        except Exception:
            pass

    if not result:
        raise RuntimeError("LLM returned empty response after retry")

    logger.info(f"LLM generated {len(result)} chars")
    return result


async def check_health() -> bool:
    """Check if Ollama is reachable and the LLM model is available."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if response.status_code == 200:
                models = [m["name"] for m in response.json().get("models", [])]
                return any(LLM_MODEL in m for m in models)
    except Exception:
        return False
    return False
