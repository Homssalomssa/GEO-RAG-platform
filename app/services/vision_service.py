"""
Vision Service — Qwen3-VL via Ollama.

Sends satellite images to the vision model and extracts
STRUCTURED features (not prose descriptions).
"""

import json
import httpx
import logging

from config import OLLAMA_BASE_URL, VISION_MODEL, OLLAMA_TIMEOUT

logger = logging.getLogger(__name__)

# The prompt that forces structured JSON output from the vision model.
# This is the most important prompt in the entire system.
VISION_EXTRACTION_PROMPT = """Analyze this satellite/aerial image and extract the following features.
Return ONLY a valid JSON object with these exact keys. No explanation, no markdown, just JSON.

{
  "vegetation_density": "describe vegetation coverage (low/medium/high, approximate percentage)",
  "building_density": "describe building density and arrangement",
  "road_density": "describe road network density and types (paved/unpaved)",
  "urban_pattern": "describe urban layout pattern (grid/irregular/radial/sprawl)",
  "expansion_signs": "describe any signs of urban expansion or new development",
  "illegal_settlement_indicators": "describe any indicators of informal/illegal settlements (irregular layout, no infrastructure, makeshift structures)"
}

Be specific and quantitative where possible. If a feature is not visible, say "not detected".
Return ONLY the JSON object."""


async def extract_features(image_base64: str) -> dict:
    """
    Send image to Qwen3-VL and extract structured features.

    Args:
        image_base64: Base64-encoded image string

    Returns:
        Dict with 6 structured feature fields

    Raises:
        ConnectionError: If Ollama is unreachable
        ValueError: If model returns unparseable output
    """
    payload = {
        "model": VISION_MODEL,
        "prompt": VISION_EXTRACTION_PROMPT,
        "images": [image_base64],
        "stream": False,
        "options": {
            "temperature": 0.1,   # Very low — we want deterministic extraction
            "num_predict": 512,
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

    raw_text = response.json().get("response", "")
    logger.info(f"Vision raw output length: {len(raw_text)} chars")

    return _parse_vision_output(raw_text)


def _parse_vision_output(raw_text: str) -> dict:
    """
    Parse the vision model's output into a structured dict.
    Attempts JSON parsing first, then falls back to regex extraction.
    """
    expected_keys = [
        "vegetation_density", "building_density", "road_density",
        "urban_pattern", "expansion_signs", "illegal_settlement_indicators"
    ]

    # Attempt 1: Direct JSON parse
    try:
        # Strip markdown code fences if the model wrapped it
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]  # Remove first line
            cleaned = cleaned.rsplit("```", 1)[0]  # Remove last fence
        cleaned = cleaned.strip()

        parsed = json.loads(cleaned)

        # Validate all expected keys exist
        result = {}
        for key in expected_keys:
            result[key] = str(parsed.get(key, "not detected"))
        return result

    except (json.JSONDecodeError, AttributeError):
        logger.warning("Direct JSON parse failed, attempting fallback extraction")

    # Attempt 2: Regex-like extraction — look for key-value patterns
    result = {}
    for key in expected_keys:
        result[key] = _extract_field(raw_text, key)

    # Check if we got anything useful
    non_empty = [v for v in result.values() if v != "extraction failed"]
    if len(non_empty) < 3:
        raise ValueError(
            f"Could not parse vision output. Raw text: {raw_text[:500]}"
        )

    return result


def _extract_field(text: str, field_name: str) -> str:
    """Try to extract a field value from unstructured text."""
    import re

    # Look for patterns like "field_name": "value" or field_name: value
    patterns = [
        rf'"{field_name}"\s*:\s*"([^"]+)"',       # JSON-style
        rf"'{field_name}'\s*:\s*'([^']+)'",        # Single-quote JSON
        rf'{field_name}\s*:\s*(.+?)(?:\n|$)',       # Plain text
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return "extraction failed"


async def check_health() -> bool:
    """Check if vision service (Ollama) is accessible."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/health")
            return response.status_code == 200
    except Exception:
        return False

