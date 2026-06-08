from __future__ import annotations

from pathlib import Path

from munk.app import AppTarget
from munk.config import MUNK_CODE_DEFAULTS, ResolvedConfig, ResolvedRuntimeConfig, resolve_runtime_config
from munk.execution.models import CaseExecutionRequest, RuntimeOverrideValue
from munk.paths import resource_path
from munk.runtime_defaults import (
    DEFAULT_ICON_CONF,
    DEFAULT_INTERVAL,
    DEFAULT_MAX_SECONDS,
    DEFAULT_MAX_SIDE,
    DEFAULT_MAX_STEPS,
    DEFAULT_MAX_TOKENS,
    DEFAULT_SETTLE_TIMEOUT,
    DEFAULT_TEMPERATURE,
    DEFAULT_VL_MAX_SIDE,
)
from munk.services.annotate_service import AnnotateService
from munk.services.doctor_service import DoctorService
from munk.services.models import AnnotateRequest
from munk.testing import TestCase


def build_case_request(
    *,
    plan_id: str,
    app_id: str,
    case: TestCase,
    app_target: AppTarget,
    device_ref: str | None = None,
    artifact_path: Path | None = None,
    assets_root: Path | None = None,
    max_steps: int = DEFAULT_MAX_STEPS,
    max_seconds: float = DEFAULT_MAX_SECONDS,
    interval: float = DEFAULT_INTERVAL,
    settle_timeout: float = DEFAULT_SETTLE_TIMEOUT,
    max_side: int = DEFAULT_MAX_SIDE,
    icon_conf: float = DEFAULT_ICON_CONF,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
    vl_max_side: int = DEFAULT_VL_MAX_SIDE,
) -> CaseExecutionRequest:
    return CaseExecutionRequest(
        plan_id=plan_id,
        case=case,
        app_id=app_id,
        app_target=app_target,
        device_ref=device_ref,
        artifact_path=artifact_path,
        assets_root=assets_root,
        runtime_overrides=build_runtime_overrides(
            max_steps=max_steps,
            max_seconds=max_seconds,
            interval=interval,
            settle_timeout=settle_timeout,
            max_side=max_side,
            icon_conf=icon_conf,
            max_tokens=max_tokens,
            temperature=temperature,
            vl_max_side=vl_max_side,
        ),
    )


def build_runtime_overrides(
    *,
    max_steps: int | None = None,
    max_seconds: float | None = None,
    interval: float | None = None,
    settle_timeout: float | None = None,
    max_side: int | None = None,
    icon_conf: float | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    vl_max_side: int | None = None,
    include_defaults: bool = True,
) -> dict[str, RuntimeOverrideValue]:
    defaults: dict[str, RuntimeOverrideValue] = MUNK_CODE_DEFAULTS.runtime.as_runtime_overrides()
    provided: dict[str, RuntimeOverrideValue | None] = {
        "max_steps": max_steps,
        "max_seconds": max_seconds,
        "interval": interval,
        "settle_timeout": settle_timeout,
        "max_side": max_side,
        "icon_conf": icon_conf,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "vl_max_side": vl_max_side,
    }

    overrides: dict[str, RuntimeOverrideValue] = {}
    for key, default_value in defaults.items():
        value = provided[key]
        if value is None:
            if include_defaults:
                overrides[key] = default_value
            continue
        overrides[key] = value
    return overrides


def build_runtime_overrides_from_config(runtime_config: ResolvedRuntimeConfig) -> dict[str, RuntimeOverrideValue]:
    return build_runtime_overrides(
        max_steps=runtime_config.max_steps,
        max_seconds=runtime_config.max_seconds,
        interval=runtime_config.interval,
        settle_timeout=runtime_config.settle_timeout,
        max_side=runtime_config.max_side,
        icon_conf=runtime_config.icon_conf,
        max_tokens=runtime_config.max_tokens,
        temperature=runtime_config.temperature,
        vl_max_side=runtime_config.vl_max_side,
    )


def build_runtime_overrides_for_cli(
    resolved_config: ResolvedConfig,
    *,
    max_steps: int | None = None,
    max_seconds: float | None = None,
    interval: float | None = None,
    settle_timeout: float | None = None,
    max_side: int | None = None,
    icon_conf: float | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    vl_max_side: int | None = None,
) -> dict[str, RuntimeOverrideValue]:
    overrides = build_runtime_overrides_from_config(resolve_runtime_config(resolved_config.config))
    overrides.update(
        build_runtime_overrides(
            max_steps=max_steps,
            max_seconds=max_seconds,
            interval=interval,
            settle_timeout=settle_timeout,
            max_side=max_side,
            icon_conf=icon_conf,
            max_tokens=max_tokens,
            temperature=temperature,
            vl_max_side=vl_max_side,
            include_defaults=False,
        )
    )
    return overrides


def doctor():
    service = DoctorService()
    return service.run()


def capture() -> Path:
    return resource_path("assets")


def annotate(
    image_path: Path,
    output_path: Path | None,
    max_side: int,
    icon_conf: float,
):
    service = AnnotateService()
    request = AnnotateRequest(
        image_path=image_path,
        output_path=output_path,
        max_side=max_side,
        icon_conf=icon_conf,
    )
    return service.run(request)
