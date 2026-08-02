from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from munk.agent_base.pydantic_model_factory import (
    check_vision_support,
    get_vision_preflight_cache_status,
)
from munk.config.load import load_config_context
from munk.config.resolve import ResolvedModelConfig, resolve_role_model_config
from munk.config.schema import GeminiSection, MunkConfig, OpenAICompatibleSection

VisionPreflightStatus = Literal["not_run", "cached_ok", "ok", "failed"]


@dataclass(frozen=True)
class VisionPreflightInfo:
    status: VisionPreflightStatus
    checked_at: str | None = None
    message: str | None = None


@dataclass(frozen=True)
class VerifyReadinessResult:
    ready: bool
    runner_configured: bool
    api_key_configured: bool
    provider: str | None
    model: str | None
    vision_preflight: VisionPreflightInfo
    missing: list[str]


class VerifyReadinessService:
    def __init__(self, *, workspace_root: Path | None = None) -> None:
        self._workspace_root = workspace_root

    def get(self) -> VerifyReadinessResult:
        config = self._load_config()
        resolved = resolve_role_model_config(config, role="runner") if config is not None else None
        return self._build_result(resolved, vision=None, probe_error=None)

    def probe(self) -> VerifyReadinessResult:
        config = self._load_config()
        resolved = resolve_role_model_config(config, role="runner") if config is not None else None
        if resolved is None:
            return self._build_result(None, vision=None, probe_error=None)
        if not _api_key_configured(resolved):
            return self._build_result(
                resolved,
                vision=VisionPreflightInfo(
                    status="failed",
                    message="api key not configured for runner model",
                ),
                probe_error=None,
            )
        try:
            check_vision_support(resolved, config=config)
        except Exception as exc:  # noqa: BLE001
            return self._build_result(
                resolved,
                vision=VisionPreflightInfo(status="failed", message=str(exc)),
                probe_error=str(exc),
            )
        cached_ok, checked_at = get_vision_preflight_cache_status(resolved)
        return self._build_result(
            resolved,
            vision=VisionPreflightInfo(
                status="ok" if cached_ok else "ok",
                checked_at=checked_at,
            ),
            probe_error=None,
        )

    def _load_config(self) -> MunkConfig | None:
        try:
            resolved = load_config_context(None, workspace_root=self._workspace_root)
        except (FileNotFoundError, OSError, ValueError):
            return MunkConfig()
        if resolved is None:
            return MunkConfig()
        return resolved.config

    def _build_result(
        self,
        resolved: ResolvedModelConfig | None,
        *,
        vision: VisionPreflightInfo | None,
        probe_error: str | None,
    ) -> VerifyReadinessResult:
        runner_configured = resolved is not None
        api_key_configured = _api_key_configured(resolved) if resolved is not None else False
        provider = resolved.provider if resolved is not None else None
        model = resolved.model if resolved is not None else None

        if vision is None and resolved is not None:
            cached_ok, checked_at = get_vision_preflight_cache_status(resolved)
            vision = VisionPreflightInfo(
                status="cached_ok" if cached_ok else "not_run",
                checked_at=checked_at if cached_ok else None,
            )
        if vision is None:
            vision = VisionPreflightInfo(status="not_run")

        missing: list[str] = []
        if not runner_configured:
            missing.append("runner_model_not_configured")
        elif not api_key_configured:
            missing.append("api_key_not_configured")
        if vision.status in {"not_run"}:
            missing.append("vision_preflight_not_run")
        elif vision.status == "failed":
            missing.append("vision_preflight_failed")
        if probe_error:
            # already covered by vision_preflight_failed; keep message on vision
            pass

        vision_ok = vision.status in {"cached_ok", "ok"}
        ready = runner_configured and api_key_configured and vision_ok
        return VerifyReadinessResult(
            ready=ready,
            runner_configured=runner_configured,
            api_key_configured=api_key_configured,
            provider=provider,
            model=model,
            vision_preflight=vision,
            missing=missing,
        )


def _api_key_configured(resolved: ResolvedModelConfig) -> bool:
    section = resolved.config_section
    if isinstance(section, OpenAICompatibleSection):
        return bool(section.api_key and section.api_key.strip())
    if isinstance(section, GeminiSection):
        if section.api_key and section.api_key.strip():
            return True
        if section.vertexai and section.credentials_path:
            return True
        return False
    return False
