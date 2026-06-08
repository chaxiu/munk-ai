from __future__ import annotations

import json


def coerce_json_container_string(value: object) -> object:
    """Parse JSON object/list strings when a structured container is expected.

    This is intentionally narrow:
    - non-strings are returned unchanged
    - only strings starting with "{" or "[" are considered
    - only parsed dict/list values are returned
    - invalid JSON or scalar JSON leaves the original string untouched
    """

    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text or text[0] not in {"{", "["}:
        return value
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return value
    if isinstance(parsed, (dict, list)):
        return parsed
    return value
