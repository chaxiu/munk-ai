from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any

import httpx
from httpx import ByteStream


def decode_http_body(body: bytes | str | None) -> object:
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


def normalize_openai_chat_request_body(
    body: object,
    *,
    request: httpx.Request,
    thinking: bool | None = None,
) -> object:
    if not is_openai_chat_completions_request(request):
        return body
    if not isinstance(body, dict):
        return body

    normalized_body: dict[str, object] = dict(body)
    body_changed = False
    messages = normalized_body.get("messages")
    if isinstance(messages, list):
        normalized_messages = normalize_openai_chat_messages(messages)
        if normalized_messages is not messages:
            normalized_body["messages"] = normalized_messages
            body_changed = True
    if thinking is not None:
        updated_body = inject_openai_chat_thinking_override(normalized_body, thinking=thinking)
        if updated_body is not normalized_body:
            normalized_body = updated_body
            body_changed = True
    return normalized_body if body_changed else body


def is_openai_chat_completions_request(request: httpx.Request) -> bool:
    return request.method.upper() == "POST" and request.url.path.endswith("/chat/completions")


def normalize_openai_chat_messages(messages: list[object]) -> list[object]:
    normalized_messages: list[object] | None = None
    for index, message in enumerate(messages):
        normalized_message = normalize_openai_chat_message(message)
        if normalized_message is not message and normalized_messages is None:
            normalized_messages = list(messages[:index])
        if normalized_messages is not None:
            normalized_messages.append(normalized_message)
    return messages if normalized_messages is None else normalized_messages


def normalize_openai_chat_message(message: object) -> object:
    if not isinstance(message, dict):
        return message
    if "role" not in message:
        return message
    if message.get("content") is not None and "content" in message:
        return message
    normalized_message = dict(message)
    normalized_message["content"] = ""
    return normalized_message


def inject_openai_chat_thinking_override(body: dict[str, object], *, thinking: bool) -> dict[str, object]:
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


def rewrite_json_request_content(request: httpx.Request, body: object) -> None:
    encoded = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    request._content = encoded
    request.stream = ByteStream(encoded)
    request.headers["content-length"] = str(len(encoded))


def normalize_json_value(value: object) -> object:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, list | tuple):
        return [normalize_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): normalize_json_value(item) for key, item in value.items()}
    return str(value)


def sanitize_transcript_payload(value: object) -> object:
    if isinstance(value, list):
        return [sanitize_transcript_payload(item) for item in value]
    if not isinstance(value, dict):
        return value

    sanitized = {
        str(key): sanitize_transcript_payload(item)
        for key, item in value.items()
    }
    image_url = sanitized.get("image_url")
    if isinstance(image_url, dict):
        url = image_url.get("url")
        if isinstance(url, str) and url.startswith("data:image/"):
            sanitized["image_url"] = summarize_data_image_url(url, image_url=image_url)
    return sanitized


def summarize_data_image_url(url: str, *, image_url: dict[str, object]) -> dict[str, object]:
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


def redact_headers(headers: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in headers.items():
        if key.lower() in {"authorization", "x-api-key", "api-key"}:
            redacted[key] = "<redacted>"
        else:
            redacted[key] = value
    return redacted
