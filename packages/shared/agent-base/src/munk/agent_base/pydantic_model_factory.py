from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, cast

import cv2
import httpx
import numpy as np
from pydantic_ai import Agent
from pydantic_ai.messages import BinaryImage, TextContent, UserContent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.openai import OpenAIProvider

from munk.config.defaults import MUNK_CODE_DEFAULTS
from munk.config.resolve import ResolvedModelConfig, resolve_runtime_config
from munk.config.schema import GeminiSection, MunkConfig, OpenAICompatibleSection
from munk.network.proxy import resolve_proxy_config
from munk.perception.image import BgrImage
from munk.user_data import cache_home

from .image_payload import EncodedImagePayload, encode_image_for_max_side

from .llm import build_transcript_http_client, run_agent_sync_compatible

_VISION_PREFLIGHT_MODEL_SETTINGS = MUNK_CODE_DEFAULTS.vision_preflight.as_model_settings()
_VISION_PREFLIGHT_CACHE_TTL = timedelta(days=7)
_VISION_PREFLIGHT_CACHE_VERSION = 1
_VISION_PREFLIGHT_CACHE_FILE = "vision_preflight_success.json"
logger = logging.getLogger(__name__)


def build_pydantic_ai_model(resolved: ResolvedModelConfig, *, config: MunkConfig | None = None) -> object:
    if resolved.provider == "openai_compatible":
        section = cast(OpenAICompatibleSection, resolved.config_section)
        return _build_openai_model(section, config=config)
    if resolved.provider == "gemini":
        section = cast(GeminiSection, resolved.config_section)
        return _build_gemini_model(section, config=config)
    raise ValueError(f"unsupported model provider: {resolved.provider}")


def build_pydantic_ai_openai_model(section: OpenAICompatibleSection, *, config: MunkConfig | None = None) -> object:
    """Backward-compatible helper for legacy OpenAI-compatible call sites."""
    return _build_openai_model(section, config=config)


def build_pydantic_openai_model(section: OpenAICompatibleSection, *, config: MunkConfig | None = None) -> object:
    """Backward-compatible alias for existing runner code paths."""
    return build_pydantic_ai_openai_model(section, config=config)


def check_vision_support(
    resolved: ResolvedModelConfig,
    *,
    config: MunkConfig | None = None,
    image_bgr: BgrImage | None = None,
) -> None:
    if _is_cached_vision_support_success(resolved):
        return
    model = build_pydantic_ai_model(resolved, config=config)
    runtime_config = resolve_runtime_config(config) if config is not None else None
    agent = Agent(
        model=cast(Any, model),
        output_type=str,
        name="vision_preflight_agent",
        model_settings=cast(Any, _VISION_PREFLIGHT_MODEL_SETTINGS),
    )
    try:
        result = run_agent_sync_compatible(
            agent,
            _build_vision_preflight_prompt(
                image_bgr=image_bgr,
                config=config,
            ),
        )
    except Exception as exc:  # noqa: BLE001
        if _should_retry_preflight_with_jpeg(exc, runtime_config=runtime_config):
            try:
                result = run_agent_sync_compatible(
                    agent,
                    _build_vision_preflight_prompt(
                        image_bgr=image_bgr,
                        config=config,
                        preferred_format="jpeg",
                        fallback_format="jpeg",
                    ),
                )
            except Exception as retry_exc:  # noqa: BLE001
                exc = retry_exc
            else:
                if not result.output.strip():
                    raise RuntimeError(
                        "configured model returned empty content during vision preflight; "
                        "please use a vision-capable model"
                    )
                _record_cached_vision_support_success(resolved)
                return
        if _is_definitive_vision_unsupported(exc):
            raise RuntimeError(
                "configured model does not appear to support vision input; "
                "munk requires a vision-capable model"
            ) from exc
        if _is_definitive_preflight_config_or_transport_error(exc):
            raise RuntimeError(
                "vision preflight failed due to provider connectivity or configuration; "
                "please verify the model endpoint, credentials, and network reachability"
            ) from exc
        if _is_inconclusive_provider_crash(exc):
            logger.warning("vision preflight inconclusive; continuing run: %s", exc)
            return
        raise RuntimeError(
            "vision preflight failed before confirming image support; "
            "please retry or inspect the provider error details"
        ) from exc
    if not result.output.strip():
        raise RuntimeError(
            "configured model returned empty content during vision preflight; "
            "please use a vision-capable model"
        )
    _record_cached_vision_support_success(resolved)


def _build_openai_model(section: OpenAICompatibleSection, *, config: MunkConfig | None = None) -> object:
    headers = dict(section.extra_headers)
    http_client = build_transcript_http_client(
        provider="openai_compatible",
        model=section.model,
        base_url=section.base_url,
        timeout=section.timeout_sec,
        headers=headers or None,
        thinking=section.thinking,
        proxy=resolve_proxy_config(config),
    )
    provider = OpenAIProvider(
        base_url=section.base_url,
        api_key=section.api_key or "unused",
        http_client=http_client,
    )
    from pydantic_ai.models.openai import OpenAIChatModel

    return OpenAIChatModel(section.model, provider=provider)


def _build_gemini_model(section: GeminiSection, *, config: MunkConfig | None = None) -> object:
    http_client = build_transcript_http_client(
        provider="gemini",
        model=section.model,
        base_url=section.base_url or "https://generativelanguage.googleapis.com",
        timeout=section.timeout_sec,
        headers=None,
        proxy=resolve_proxy_config(config),
    )
    credentials = None
    if section.credentials_path:
        from google.oauth2 import service_account

        credentials = service_account.Credentials.from_service_account_file(
            section.credentials_path,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )

    provider_factory = cast(Any, GoogleProvider)
    provider_kwargs: dict[str, object] = {
        "api_key": section.api_key,
        "project": section.project,
        "location": section.location,
        "vertexai": section.vertexai,
        "http_client": http_client,
        "base_url": section.base_url,
    }
    if credentials is not None:
        provider_kwargs["credentials"] = credentials
    provider = provider_factory(
        **provider_kwargs,
    )
    return GoogleModel(section.model, provider=provider)


def _build_vision_preflight_prompt(
    *,
    image_bgr: BgrImage | None = None,
    config: MunkConfig | None = None,
    preferred_format: str | None = None,
    fallback_format: str | None = None,
) -> list[UserContent]:
    image_payload = _encode_preflight_image_payload(
        image_bgr=image_bgr,
        config=config,
        preferred_format=preferred_format,
        fallback_format=fallback_format,
    )
    return [
        TextContent(content="Reply with OK."),
        BinaryImage(
            image_payload.data,
            media_type=image_payload.media_type,
            identifier="vision_preflight",
        ),
    ]


def _is_definitive_vision_unsupported(exc: Exception) -> bool:
    text = str(exc).lower()
    signals = (
        "does not support vision",
        "doesn't support vision",
        "does not support image",
        "doesn't support image",
        "does not appear to support vision",
        "vision input",
        "image input",
        "multimodal",
        "text-only",
        "text only",
        "unsupported image",
        "image_url is only supported",
        "image_url not supported",
    )
    return any(signal in text for signal in signals)


def _is_definitive_preflight_config_or_transport_error(exc: Exception) -> bool:
    if isinstance(exc, httpx.TimeoutException | httpx.NetworkError):
        return True
    text = str(exc).lower()
    signals = (
        "api key",
        "authentication",
        "unauthorized",
        "forbidden",
        "permission denied",
        "invalid credentials",
        "incorrect api key",
        "connection refused",
        "connection error",
        "network is unreachable",
        "name or service not known",
        "temporary failure in name resolution",
        "nodename nor servname provided",
        "connect timeout",
        "read timeout",
        "timed out",
        "404",
        "401",
        "403",
        "not found",
    )
    return any(signal in text for signal in signals)


def _is_inconclusive_provider_crash(exc: Exception) -> bool:
    text = str(exc).lower()
    signals = (
        "model has crashed",
        "provider crashed",
        "server disconnected without sending a response",
        "connection reset by peer",
        "remote protocol error",
        "internal server error",
        "bad gateway",
        "service unavailable",
        "gateway timeout",
        "exit code: null",
    )
    return any(signal in text for signal in signals)


def _encode_preflight_image_payload(
    *,
    image_bgr: BgrImage | None = None,
    config: MunkConfig | None = None,
    preferred_format: str | None = None,
    fallback_format: str | None = None,
) -> EncodedImagePayload:
    runtime_config = resolve_runtime_config(config) if config is not None else MUNK_CODE_DEFAULTS.runtime
    if image_bgr is None:
        image = np.zeros((256, 256, 3), dtype=np.uint8)
        image[:, :] = (255, 160, 64)
        cv2.rectangle(image, (24, 24), (232, 232), (255, 255, 255), thickness=6)
        cv2.putText(image, "OK", (72, 156), cv2.FONT_HERSHEY_SIMPLEX, 2.6, (0, 0, 0), 6, cv2.LINE_AA)
    else:
        image: BgrImage = image_bgr
    payload = encode_image_for_max_side(
        image,
        getattr(runtime_config, "vl_max_side", MUNK_CODE_DEFAULTS.runtime.vl_max_side),
        preferred_format=preferred_format or getattr(runtime_config, "vl_image_format", MUNK_CODE_DEFAULTS.runtime.vl_image_format),
        fallback_format=fallback_format or getattr(
            runtime_config,
            "vl_fallback_image_format",
            MUNK_CODE_DEFAULTS.runtime.vl_fallback_image_format,
        ),
        webp_quality=getattr(runtime_config, "vl_webp_quality", MUNK_CODE_DEFAULTS.runtime.vl_webp_quality),
        jpeg_quality=getattr(runtime_config, "vl_jpeg_quality", MUNK_CODE_DEFAULTS.runtime.vl_jpeg_quality),
    )
    if payload is None:
        raise RuntimeError("failed to encode vision preflight image")
    return payload


def _should_retry_preflight_with_jpeg(exc: Exception, *, runtime_config: object | None) -> bool:
    preferred_format = getattr(runtime_config, "vl_image_format", MUNK_CODE_DEFAULTS.runtime.vl_image_format)
    if preferred_format != "webp":
        return False
    text = str(exc).lower()
    signals = (
        "webp",
        "image/webp",
        "unsupported image",
        "unsupported format",
        "invalid image",
    )
    return any(signal in text for signal in signals)


def get_vision_preflight_cache_status(
    resolved: ResolvedModelConfig,
) -> tuple[bool, str | None]:
    """Return (cached_ok, checked_at_iso) for the resolved runner model. Does not call the LLM."""
    payload = _load_preflight_cache()
    if payload is None:
        return False, None
    key = _vision_preflight_cache_key(resolved)
    entry = payload.get("entries", {}).get(key)
    if not isinstance(entry, dict):
        return False, None
    checked_at_raw = entry.get("checked_at")
    if not isinstance(checked_at_raw, str):
        return False, None
    try:
        checked_at = datetime.fromisoformat(checked_at_raw)
    except ValueError:
        return False, None
    if checked_at.tzinfo is None:
        checked_at = checked_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - checked_at > _VISION_PREFLIGHT_CACHE_TTL:
        return False, checked_at.isoformat()
    return True, checked_at.isoformat()


def _is_cached_vision_support_success(resolved: ResolvedModelConfig) -> bool:
    cached_ok, _checked_at = get_vision_preflight_cache_status(resolved)
    return cached_ok


def _record_cached_vision_support_success(resolved: ResolvedModelConfig) -> None:
    path = _vision_preflight_cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _load_preflight_cache() or {
        "version": _VISION_PREFLIGHT_CACHE_VERSION,
        "entries": {},
    }
    entries = payload.setdefault("entries", {})
    if not isinstance(entries, dict):
        entries = {}
        payload["entries"] = entries
    entries[_vision_preflight_cache_key(resolved)] = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    valid_entries: dict[str, dict[str, str]] = {}
    for key, value in entries.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            continue
        checked_at = value.get("checked_at")
        if isinstance(checked_at, str):
            valid_entries[key] = {"checked_at": checked_at}
    payload["version"] = _VISION_PREFLIGHT_CACHE_VERSION
    payload["entries"] = valid_entries
    path.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2), encoding="utf-8")


def _load_preflight_cache() -> dict[str, Any] | None:
    path = _vision_preflight_cache_path()
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("version") != _VISION_PREFLIGHT_CACHE_VERSION:
        return None
    return payload


def _vision_preflight_cache_path() -> Path:
    return cache_home() / _VISION_PREFLIGHT_CACHE_FILE


def _vision_preflight_cache_key(resolved: ResolvedModelConfig) -> str:
    section_payload = _vision_preflight_section_payload(resolved)
    raw = json.dumps(
        {
            "provider": resolved.provider,
            "model": resolved.model,
            "section": section_payload,
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _vision_preflight_section_payload(resolved: ResolvedModelConfig) -> dict[str, Any]:
    section = resolved.config_section
    if isinstance(section, OpenAICompatibleSection):
        return {
            "base_url": section.base_url,
            "model": section.model,
            "timeout_sec": section.timeout_sec,
            "extra_headers": dict(section.extra_headers),
            "api_key_sha256": _secret_fingerprint(section.api_key),
        }
    return {
        "model": section.model,
        "timeout_sec": section.timeout_sec,
        "vertexai": section.vertexai,
        "project": section.project,
        "location": section.location,
        "base_url": section.base_url,
        "api_key_sha256": _secret_fingerprint(section.api_key),
    }


def _secret_fingerprint(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
