from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, cast

from munk.token_usage import TokenUsage
from munk.user_data import cache_home

from .transcript_models import (
    ENV_LLM_TRANSCRIPT,
    JsonValue,
    LlmRequestTranscriptEntry,
    LlmResponseTranscriptEntry,
    LlmTranscriptEntry,
    get_scoped_transcript_path,
    get_transcript_observer,
)
from .transcript_payloads import normalize_json_value, sanitize_transcript_payload

_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}
_logger = logging.getLogger(__name__)


def should_capture_llm_transcript() -> bool:
    raw = os.environ.get(ENV_LLM_TRANSCRIPT)
    if raw is not None:
        normalized = raw.strip().lower()
        if normalized in _TRUE_VALUES:
            return True
        if normalized in _FALSE_VALUES:
            return False
    return True


def prepare_llm_transcript_path(root_dir: Path) -> Path | None:
    if not should_capture_llm_transcript():
        return None
    path = root_dir / "llm_transcript.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)
    return path


def append_llm_request_entry(
    *,
    provider: str,
    model: str,
    request_id: str,
    method: str,
    url: str,
    headers: Mapping[str, object],
    body: object,
) -> None:
    write_transcript_entry(
        LlmRequestTranscriptEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            provider=provider,
            model=model,
            request_id=request_id,
            method=method,
            url=url,
            headers=cast(dict[str, JsonValue], sanitize_transcript_payload(normalize_json_value(dict(headers)))),
            body=cast(JsonValue, sanitize_transcript_payload(normalize_json_value(body))),
        )
    )


def append_llm_response_entry(
    *,
    provider: str,
    model: str,
    request_id: str,
    method: str,
    url: str,
    status_code: int,
    headers: Mapping[str, object],
    body: object,
    token_usage: TokenUsage | None,
) -> None:
    write_transcript_entry(
        LlmResponseTranscriptEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            provider=provider,
            model=model,
            request_id=request_id,
            method=method,
            url=url,
            status_code=status_code,
            headers=cast(dict[str, JsonValue], sanitize_transcript_payload(normalize_json_value(dict(headers)))),
            body=cast(JsonValue, sanitize_transcript_payload(normalize_json_value(body))),
            token_usage=token_usage,
        )
    )


def write_transcript_entry(entry: LlmTranscriptEntry) -> None:
    path = resolve_transcript_path()
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file_handle:
        file_handle.write(entry.model_dump_json(exclude_none=True))
        file_handle.write("\n")
    observer = get_transcript_observer()
    if observer is None:
        return
    try:
        observer(entry)
    except Exception:  # noqa: BLE001
        _logger.warning("failed to publish llm transcript observer event", exc_info=True)


def resolve_transcript_path() -> Path | None:
    scoped = get_scoped_transcript_path()
    if scoped is not None:
        return scoped
    if not should_capture_llm_transcript():
        return None
    path = cache_home() / "llm_transcript.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
