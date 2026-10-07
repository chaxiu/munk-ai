from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from munk.services.operations.paths import operation_dir, operations_root

# Large nested result fields that belong on disk, not in the listing index.
EXTERNALIZED_RESULT_KEYS = ("attempts", "evidence", "event_history")
LLM_EVENT_TYPES = frozenset({"llm_request", "llm_response"})
LLM_TEXT_KEY = "llm_text"
LLM_TEXT_PATH_KEY = "llm_text_path"
LLM_ENTRY_KEY = "llm_entry"


def resolve_operation_dir(operation_id: str, *, root: Path | None = None) -> Path:
    if root is None:
        return operation_dir(operation_id)
    path = root / "items" / operation_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def operation_result_path(operation_id: str, *, root: Path | None = None) -> Path:
    return resolve_operation_dir(operation_id, root=root) / "result.json"


def operation_event_payload_path(
    operation_id: str,
    *,
    seq: int,
    event_type: str,
    root: Path | None = None,
) -> Path:
    events_dir = resolve_operation_dir(operation_id, root=root) / "events"
    events_dir.mkdir(parents=True, exist_ok=True)
    safe_type = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in event_type)
    return events_dir / f"{seq:06d}_{safe_type}.json"


def should_externalize_result(result_json: dict[str, Any] | None) -> bool:
    if not isinstance(result_json, dict):
        return False
    return any(key in result_json for key in EXTERNALIZED_RESULT_KEYS)


def split_result_for_storage(
    result_json: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Return (inline_summary, external_payload).

    When externalization is needed, `inline_summary` keeps small fields for projections
    and `external_payload` is the full result written to disk.
    """
    if not isinstance(result_json, dict):
        return result_json, None
    if not should_externalize_result(result_json):
        return result_json, None
    external_payload = dict(result_json)
    inline_summary = {
        key: value
        for key, value in result_json.items()
        if key not in EXTERNALIZED_RESULT_KEYS
    }
    return inline_summary, external_payload


def write_external_result(
    *,
    operation_id: str,
    payload: dict[str, Any],
    root: Path | None = None,
) -> str:
    path = operation_result_path(operation_id, root=root)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def load_external_result(result_path: str | None) -> dict[str, Any] | None:
    if not isinstance(result_path, str) or not result_path.strip():
        return None
    path = Path(result_path)
    if not path.is_file():
        return None
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        return None
    return loaded


def merge_result_payload(
    *,
    inline_result: dict[str, Any] | None,
    result_path: str | None,
) -> dict[str, Any] | None:
    external = load_external_result(result_path)
    if external is None:
        return inline_result
    if not isinstance(inline_result, dict):
        return external
    merged = dict(inline_result)
    for key in EXTERNALIZED_RESULT_KEYS:
        if key in external:
            merged[key] = external[key]
    for key, value in external.items():
        if key not in merged:
            merged[key] = value
    return merged


def extract_llm_text_for_storage(data_json: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    """Strip large LLM fields from event payload; return (inline_payload, external_text)."""
    inline = dict(data_json)
    # Legacy rows may embed the full transcript object; keep only summary metadata in SQLite.
    inline.pop(LLM_ENTRY_KEY, None)
    text = inline.get(LLM_TEXT_KEY)
    if not isinstance(text, str) or not text:
        inline.pop(LLM_TEXT_KEY, None)
        changed = inline != data_json
        return (inline, None) if changed else (data_json, None)
    inline.pop(LLM_TEXT_KEY, None)
    return inline, text


def write_external_llm_text(
    *,
    operation_id: str,
    seq: int,
    event_type: str,
    text: str,
    root: Path | None = None,
) -> str:
    path = operation_event_payload_path(
        operation_id,
        seq=seq,
        event_type=event_type,
        root=root,
    )
    path.write_text(text, encoding="utf-8")
    return str(path)


def hydrate_event_data_json(data_json: dict[str, Any] | None) -> dict[str, Any]:
    payload = dict(data_json or {})
    text_path = payload.get(LLM_TEXT_PATH_KEY)
    if isinstance(text_path, str) and text_path.strip() and LLM_TEXT_KEY not in payload:
        path = Path(text_path)
        if path.is_file():
            payload[LLM_TEXT_KEY] = path.read_text(encoding="utf-8")
    return payload


def default_operations_root() -> Path:
    return operations_root()
