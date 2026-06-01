from __future__ import annotations

import base64
import hashlib
import json
import os
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping
from uuid import uuid4

import httpx
from httpx import ByteStream

from munk.network.proxy import ResolvedProxyConfig, build_httpx_proxy_kwargs
from munk.runtime_distribution import resolve_runtime_layout
from munk.user_data import cache_home

ENV_LLM_TRANSCRIPT = "MUNK_LLM_TRANSCRIPT"
_TRANSCRIPT_PATH: ContextVar[Path | None] = ContextVar("munk_llm_transcript_path", default=None)
_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


def build_transcript_http_client(
    *,
    provider: str,
    model: str,
    base_url: str,
    timeout: float,
    headers: Mapping[str, str] | None,
    thinking: bool | None = None,
    proxy: ResolvedProxyConfig | None = None,
) -> httpx.AsyncClient:
    base_headers = dict(headers or {})

    async def on_request(request: httpx.Request) -> None:
        request_id = uuid4().hex
        request.extensions["munk_llm_request_id"] = request_id
        decoded_body = _decode_http_body(request.content)
        normalized_body = _normalize_openai_chat_request_body(
            decoded_body,
            request=request,
            thinking=thinking,
        )
        if normalized_body is not decoded_body:
            _rewrite_json_request_content(request, normalized_body)
        payload = {
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "headers": _redact_headers(dict(request.headers)),
            "body": normalized_body,
        }
        append_transcript_entry(
            kind="llm_request",
            provider=provider,
            model=model,
            payload=payload,
        )

    async def on_response(response: httpx.Response) -> None:
        request = response.request
        request_id = str(request.extensions.get("munk_llm_request_id", ""))
        try:
            await response.aread()
            body: object = _decode_http_body(response.content)
        except Exception as exc:  # noqa: BLE001
            body = {"read_error": str(exc)}
        payload = {
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "status_code": response.status_code,
            "headers": _redact_headers(dict(response.headers)),
            "body": body,
        }
        append_transcript_entry(
            kind="llm_response",
            provider=provider,
            model=model,
            payload=payload,
        )

    return httpx.AsyncClient(
        timeout=timeout,
        headers=base_headers or None,
        event_hooks={
            "request": [on_request],
            "response": [on_response],
        },
        **build_httpx_proxy_kwargs(url=base_url, proxy=proxy),
    )


def should_capture_llm_transcript() -> bool:
    raw = os.environ.get(ENV_LLM_TRANSCRIPT)
    if raw is not None:
        normalized = raw.strip().lower()
        if normalized in _TRUE_VALUES:
            return True
        if normalized in _FALSE_VALUES:
            return False

    layout = resolve_runtime_layout()
    if layout.layout_mode == "development":
        return True
    return layout.runtime_root.name == "runtime-dev"


def prepare_llm_transcript_path(root_dir: Path) -> Path | None:
    if not should_capture_llm_transcript():
        return None
    path = root_dir / "llm_transcript.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)
    return path


@contextmanager
def llm_transcript_scope(path: Path | None) -> Iterator[None]:
    token = _TRANSCRIPT_PATH.set(path)
    try:
        yield
    finally:
        _TRANSCRIPT_PATH.reset(token)


def append_transcript_entry(
    *,
    kind: str,
    provider: str,
    model: str,
    payload: Mapping[str, object],
) -> None:
    path = _resolve_transcript_path()
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "kind": kind,
        "provider": provider,
        "model": model,
        "payload": _sanitize_transcript_payload(_normalize_json_value(dict(payload))),
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False))
        f.write("\n")


def _resolve_transcript_path() -> Path | None:
    scoped = _TRANSCRIPT_PATH.get()
    if scoped is not None:
        return scoped
    if not should_capture_llm_transcript():
        return None
    path = cache_home() / "llm_transcript.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _decode_http_body(body: bytes | str | None) -> object:
    if body is None:
        return None
    raw = body.decode("utf-8", errors="replace") if isinstance(body, bytes) else body
    text = raw.strip()
    if not text:
        return ""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return raw


def _normalize_openai_chat_request_body(
    body: object,
    *,
    request: httpx.Request,
    thinking: bool | None = None,
) -> object:
    if not _is_openai_chat_completions_request(request):
        return body
    if not isinstance(body, dict):
        return body
    body_changed = False
    normalized_body = body
    messages = body.get("messages")
    if isinstance(messages, list):
        normalized_messages = _normalize_openai_chat_messages(messages)
        if normalized_messages is not messages:
            normalized_body = {
                **normalized_body,
                "messages": normalized_messages,
            }
            body_changed = True
    if thinking is not None:
        thinking_body = _inject_openai_chat_thinking_override(normalized_body, thinking=thinking)
        if thinking_body is not normalized_body:
            normalized_body = thinking_body
            body_changed = True
    return normalized_body if body_changed else body


def _is_openai_chat_completions_request(request: httpx.Request) -> bool:
    return request.method.upper() == "POST" and request.url.path.endswith("/chat/completions")


def _normalize_openai_chat_messages(messages: list[object]) -> list[object]:
    normalized_messages: list[object] | None = None
    for index, message in enumerate(messages):
        normalized_message = _normalize_openai_chat_message(message)
        if normalized_message is not message and normalized_messages is None:
            normalized_messages = list(messages[:index])
        if normalized_messages is not None:
            normalized_messages.append(normalized_message)
    return messages if normalized_messages is None else normalized_messages


def _normalize_openai_chat_message(message: object) -> object:
    if not isinstance(message, dict):
        return message
    if "role" not in message:
        return message
    if message.get("content") is not None and "content" in message:
        return message
    return {
        **message,
        "content": "",
    }


def _inject_openai_chat_thinking_override(body: object, *, thinking: bool) -> object:
    if not isinstance(body, dict):
        return body
    extra_body = body.get("extra_body")
    if extra_body is None:
        return {
            **body,
            "extra_body": {"enable_thinking": thinking},
        }
    if not isinstance(extra_body, dict):
        return body
    if "enable_thinking" in extra_body:
        return body
    return {
        **body,
        "extra_body": {
            **extra_body,
            "enable_thinking": thinking,
        },
    }


def _rewrite_json_request_content(request: httpx.Request, body: object) -> None:
    encoded = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    request._content = encoded
    request.stream = ByteStream(encoded)
    request.headers["content-length"] = str(len(encoded))


def _normalize_json_value(value: object) -> object:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, list | tuple):
        return [_normalize_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize_json_value(item) for key, item in value.items()}
    return str(value)


def _sanitize_transcript_payload(value: object) -> object:
    if isinstance(value, list):
        return [_sanitize_transcript_payload(item) for item in value]
    if not isinstance(value, dict):
        return value

    sanitized = {
        str(key): _sanitize_transcript_payload(item)
        for key, item in value.items()
    }
    image_url = sanitized.get("image_url")
    if isinstance(image_url, dict):
        url = image_url.get("url")
        if isinstance(url, str) and url.startswith("data:image/"):
            sanitized["image_url"] = _summarize_data_image_url(url, image_url=image_url)
    return sanitized


def _summarize_data_image_url(url: str, *, image_url: dict[str, object]) -> dict[str, object]:
    prefix, _, encoded = url.partition(",")
    media_type = prefix[5:].split(";", 1)[0] if prefix.startswith("data:") else "image/unknown"
    decoded = b""
    if encoded:
        try:
            decoded = base64.b64decode(encoded, validate=False)
        except Exception:  # noqa: BLE001
            decoded = b""
    approx_bytes = len(decoded) if decoded else None
    sha256 = hashlib.sha256(decoded).hexdigest() if decoded else None
    return {
        **image_url,
        "url": "<omitted:data-image>",
        "media_type": media_type,
        "sha256": sha256,
        "approx_bytes": approx_bytes,
    }


def _redact_headers(headers: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in headers.items():
        if key.lower() in {"authorization", "x-api-key", "api-key"}:
            redacted[key] = "<redacted>"
        else:
            redacted[key] = value
    return redacted
