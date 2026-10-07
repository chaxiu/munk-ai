from __future__ import annotations

import hashlib
import json
from typing import Any


def canonicalize_json(value: Any) -> Any:
    """Deterministic JSON for hashing: sorted object keys, stable arrays.

    Integer-valued floats are normalized to ``int`` so the digest matches
    JavaScript ``JSON.stringify`` (``300.0`` → ``300``), which the BFF uses.
    """
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        return value
    if isinstance(value, list):
        return [canonicalize_json(item) for item in value]
    if isinstance(value, dict):
        return {key: canonicalize_json(value[key]) for key in sorted(value.keys())}
    raise TypeError(f"Unsupported JSON value type for hashing: {type(value)!r}")


def sha256_hex(input_text: str) -> str:
    return hashlib.sha256(input_text.encode("utf-8")).hexdigest()


def profile_to_hash_object(app_profile: dict[str, Any]) -> dict[str, Any]:
    """Align with BFF profileToHashObject (includes config/metadata bags)."""
    return {
        "app_id": app_profile.get("app_id"),
        "app_name": app_profile.get("app_name"),
        "platform": app_profile.get("platform"),
        "app_introduction_ref": app_profile.get("app_introduction_ref") or "introduction.md",
        "app_knowledge_ref": app_profile.get("app_knowledge_ref") or "app_knowledge.json",
        "android": app_profile.get("android"),
        "ios": app_profile.get("ios"),
        "web": app_profile.get("web"),
        "config": app_profile.get("config") if isinstance(app_profile.get("config"), dict) else {},
        "metadata": app_profile.get("metadata") if isinstance(app_profile.get("metadata"), dict) else {},
    }


def hash_bundle_content(
    *,
    app_id: str,
    app_profile: dict[str, Any],
    introduction: str | None,
    knowledge_document: dict[str, Any] | None,
    plans: list[Any],
    team_config: dict[str, Any],
) -> str:
    """SHA-256 over canonical payload (excludes revision). Matches BFF hashBundleContent."""
    payload = canonicalize_json(
        {
            "app_id": app_id,
            "app_profile": profile_to_hash_object(app_profile),
            "introduction": introduction,
            "knowledge_document": knowledge_document,
            "plans": plans,
            "team_config": team_config if isinstance(team_config, dict) else {},
        }
    )
    return sha256_hex(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
