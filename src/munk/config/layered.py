"""Explicit shared/local config layering for offline-first + optional cloud sync.

On-disk shape (new)::

    shared:   # syncable → cloud Bundle team_config
      provider / runtime / orchestration / agents / providers (no secrets) / ...
    local:    # never uploaded
      api_key / proxy / ios_bridge / perception.cache_dir / ...

Effective config is ``deep_merge(shared, local)`` validated as ``MunkConfig``.

Wire name on the BFF remains ``team_config``; local code uses ``shared``.
BFF still sanitizes secrets as a safety net — see
``munk-web/server/utils/cloud/teamConfig.ts``.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, cast

# Align with munk-web/server/utils/cloud/teamConfig.ts
SECRET_KEYS = frozenset(
    {
        "api_key",
        "sudo_password",
        "credentials_path",
        "password",
        "secret",
        "token",
        "access_token",
        "refresh_token",
    }
)

LOCAL_TOP_LEVEL = frozenset({"proxy", "ios_bridge"})

SHARED_TOP_LEVEL = frozenset(
    {
        "provider",
        "openai_compatible",
        "gemini",
        "agents",
        "perception",
        "test_env",
        "runtime",
        "orchestration",
    }
)

_SHARED_KEY = "shared"
_LOCAL_KEY = "local"
_LAYER_ROOT_KEYS = frozenset({_SHARED_KEY, _LOCAL_KEY})


def is_layered_document(raw: Mapping[str, Any]) -> bool:
    """True when the document uses explicit shared/local sections."""
    if _SHARED_KEY not in raw and _LOCAL_KEY not in raw:
        return False
    foreign = set(raw.keys()) - _LAYER_ROOT_KEYS
    if not foreign:
        return True
    shared = raw.get(_SHARED_KEY)
    local = raw.get(_LOCAL_KEY)
    return isinstance(shared, dict) or isinstance(local, dict)


def deep_merge(base: Mapping[str, Any], overlay: Mapping[str, Any]) -> dict[str, Any]:
    """Deep-merge mappings; overlay wins on scalar/list conflict."""
    result: dict[str, Any] = deepcopy(dict(base))
    for key, value in overlay.items():
        existing = result.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            result[key] = deep_merge(
                cast(Mapping[str, Any], existing),
                cast(Mapping[str, Any], value),
            )
        else:
            result[key] = deepcopy(value)
    return result


def merge_shared_local(
    shared: Mapping[str, Any] | None,
    local: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return deep_merge(shared or {}, local or {})


def _as_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return cast(dict[str, Any], deepcopy(value))
    return {}


def parse_layered_document(raw: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (shared, local) from a layered or flat document.

    Flat documents are split by ownership rules without mutating ``raw``.
    """
    if is_layered_document(raw):
        return _as_mapping(raw.get(_SHARED_KEY)), _as_mapping(raw.get(_LOCAL_KEY))
    return split_flat_to_layered(raw)


def effective_config_dict(raw: Mapping[str, Any]) -> dict[str, Any]:
    shared, local = parse_layered_document(raw)
    return merge_shared_local(shared, local)


def build_layered_document(
    shared: Mapping[str, Any] | None,
    local: Mapping[str, Any] | None,
) -> dict[str, Any]:
    document: dict[str, Any] = {}
    shared_clean = sanitize_shared_for_sync(shared or {})
    local_clean = _as_mapping(local)
    if shared_clean:
        document[_SHARED_KEY] = shared_clean
    if local_clean:
        document[_LOCAL_KEY] = local_clean
    return document


def strip_secret_keys(value: Any) -> Any:
    if isinstance(value, list):
        return [strip_secret_keys(item) for item in cast(list[Any], value)]
    if not isinstance(value, dict):
        return deepcopy(value)
    result: dict[str, Any] = {}
    for key, child in cast(dict[str, Any], value).items():
        if key in SECRET_KEYS:
            continue
        result[key] = strip_secret_keys(child)
    return result


def extract_secret_keys(value: Any) -> Any | None:
    """Return a parallel structure containing only SECRET_KEYS paths."""
    if isinstance(value, list):
        items = [extract_secret_keys(item) for item in cast(list[Any], value)]
        filtered = [item for item in items if item is not None]
        return filtered or None
    if not isinstance(value, dict):
        return None
    result: dict[str, Any] = {}
    for key, child in cast(dict[str, Any], value).items():
        if key in SECRET_KEYS:
            result[key] = deepcopy(child)
            continue
        nested = extract_secret_keys(child)
        if nested is not None:
            result[key] = nested
    return result or None


def _sanitize_provider(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _sanitize_perception(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    cleaned = cast(dict[str, Any], strip_secret_keys(value))
    cleaned.pop("cache_dir", None)
    return cleaned or None


def _sanitize_shared_entry(key: str, value: Any) -> Any | None:
    if key == "provider":
        return _sanitize_provider(value)
    if key == "perception":
        return _sanitize_perception(value)
    if isinstance(value, dict | list):
        return strip_secret_keys(value)
    if value is not None:
        return deepcopy(value)
    return None


def sanitize_shared_for_sync(shared: Mapping[str, Any]) -> dict[str, Any]:
    """Ensure shared payload has no secrets / local-only top-level keys.

    Mirrors BFF ``sanitizeTeamConfig`` intent so Local never writes secrets
    into the syncable section.
    """
    result: dict[str, Any] = {}
    for key, value in shared.items():
        if key in LOCAL_TOP_LEVEL or key not in SHARED_TOP_LEVEL:
            continue
        cleaned = _sanitize_shared_entry(key, value)
        if cleaned is not None:
            result[key] = cleaned
    return result


def _split_perception(value: Any) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not isinstance(value, dict):
        return None, None
    perception = cast(dict[str, Any], value)
    cache_dir = perception.get("cache_dir")
    shared_perception = cast(dict[str, Any], strip_secret_keys(perception))
    shared_perception.pop("cache_dir", None)
    secrets = extract_secret_keys(perception)
    local_perception: dict[str, Any] = {}
    if isinstance(secrets, dict):
        local_perception.update(secrets)
    if isinstance(cache_dir, str) and cache_dir.strip():
        local_perception["cache_dir"] = cache_dir.strip()
    return (shared_perception or None), (local_perception or None)


def _split_mapping_section(value: Mapping[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    shared_section = cast(dict[str, Any], strip_secret_keys(dict(value)))
    secrets = extract_secret_keys(dict(value))
    local_section = secrets if isinstance(secrets, dict) and secrets else None
    return (shared_section or None), local_section


def _assign_local_only(key: str, value: Any, local: dict[str, Any]) -> bool:
    if key in LOCAL_TOP_LEVEL:
        if isinstance(value, dict) or value is not None:
            local[key] = deepcopy(value)
        return True
    if key not in SHARED_TOP_LEVEL:
        if value is not None:
            local[key] = deepcopy(value)
        return True
    return False


def _assign_shared_section(
    key: str,
    value: Any,
    shared: dict[str, Any],
    local: dict[str, Any],
) -> None:
    if key == "provider":
        provider = _sanitize_provider(value)
        if provider is not None:
            shared["provider"] = provider
        return
    if key == "perception":
        shared_part, local_part = _split_perception(value)
        if shared_part is not None:
            shared["perception"] = shared_part
        if local_part is not None:
            local["perception"] = local_part
        return
    if not isinstance(value, dict):
        shared[key] = deepcopy(value)
        return
    shared_part, local_part = _split_mapping_section(cast(Mapping[str, Any], value))
    if shared_part is not None:
        shared[key] = shared_part
    if local_part is not None:
        local[key] = local_part


def _assign_split_key(
    key: str,
    value: Any,
    shared: dict[str, Any],
    local: dict[str, Any],
) -> None:
    if _assign_local_only(key, value, local):
        return
    _assign_shared_section(key, value, shared, local)


def split_flat_to_layered(flat: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Split a legacy flat MunkConfig dict into shared + local sections."""
    shared: dict[str, Any] = {}
    local: dict[str, Any] = {}
    for key, value in flat.items():
        if key in _LAYER_ROOT_KEYS:
            continue
        _assign_split_key(key, value, shared, local)
    return shared, local


def replace_shared_in_document(
    raw: Mapping[str, Any],
    new_shared: Mapping[str, Any],
) -> dict[str, Any]:
    """Replace shared section; preserve local (from layered or flat split)."""
    _, local = parse_layered_document(raw)
    return build_layered_document(sanitize_shared_for_sync(new_shared), local)


def read_shared_for_sync(raw: Mapping[str, Any]) -> dict[str, Any]:
    shared, _ = parse_layered_document(raw)
    return sanitize_shared_for_sync(shared)


def ensure_no_secrets_in_shared(shared: Mapping[str, Any]) -> None:
    """Raise ValueError if shared still contains secret keys (safety net)."""

    def _walk(node: Any, path: str) -> None:
        if isinstance(node, list):
            for index, item in enumerate(cast(list[Any], node)):
                _walk(item, f"{path}[{index}]")
            return
        if not isinstance(node, dict):
            return
        for key, child in cast(dict[str, Any], node).items():
            child_path = f"{path}.{key}" if path else key
            if key in SECRET_KEYS:
                raise ValueError(f"shared config must not contain secret key: {child_path}")
            if key in LOCAL_TOP_LEVEL and path == "":
                raise ValueError(f"shared config must not contain local-only top-level key: {key}")
            _walk(child, child_path)

    _walk(dict(shared), "")
