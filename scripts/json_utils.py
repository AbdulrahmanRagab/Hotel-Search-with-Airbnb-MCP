import json
import re
from typing import Any


def _extract_json(raw: str) -> dict[str, Any]:
    """Extracts JSON from the model's response even if there is extra text or markdown fences."""
    if not raw or not raw.strip():
        raise ValueError("Empty response from LLM")

    text = raw.strip()

    if "```" in text:
        text = re.sub(r"```(?:json)?", "", text).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]

    return json.loads(text)
