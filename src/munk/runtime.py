from __future__ import annotations

from pathlib import Path

from munk.app import AppTarget
from munk.config import MUNK_CODE_DEFAULTS, ResolvedConfig, ResolvedRuntimeConfig, resolve_runtime_config
from munk.config.resolve import RuntimeOverridePatch
from munk.execution.models import CaseExecutionRequest, RuntimeOverrideValue
from munk.paths import resource_path
from munk.runtime_defaults import (
    DEFAULT_ICON_CONF,
    DEFAULT_INITIAL_READY_TIMEOUT_SEC,
    DEFAULT_INTERVAL,
    DEFAULT_MAX_SECONDS,
    DEFAULT_MAX_SIDE,
    DEFAULT_MAX_STEPS,
    DEFAULT_MAX_TOKENS,
    DEFAULT_RUNNER_MAX_ELEMENTS,
    DEFAULT_RUNNER_INCLUDE_SCREENSHOT,
    DEFAULT_SETTLE_DELAY_SEC,
    DEFAULT_SETTLE_MODE,
    DEFAULT_SETTLE_OCR_ONLY,
    DEFAULT_SETTLE_RATIO_THRESHOLD,
    DEFAULT_SETTLE_TIMEOUT,
    DEFAULT_TEMPERATURE,
    DEFAULT_VL_FALLBACK_IMAGE_FORMAT,
    DEFAULT_VL_IMAGE_FORMAT,
    DEFAULT_VL_JPEG_QUALITY,
    DEFAULT_VL_MAX_SIDE,
    DEFAULT_VL_WEBP_QUALITY,
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
    runtime_patch: RuntimeOverridePatch | None = None,
    max_steps: int = DEFAULT_MAX_STEPS,
    max_seconds: float = DEFAULT_MAX_SECONDS,
    interval: float = DEFAULT_INTERVAL,
    settle_timeout: float = DEFAULT_SETTLE_TIMEOUT,
    initial_ready_timeout_sec: float = DEFAULT_INITIAL_READY_TIMEOUT_SEC,
    settle_mode: str = DEFAULT_SETTLE_MODE,
    settle_ocr_only: bool = DEFAULT_SETTLE_OCR_ONLY,
    settle_ratio_threshold: float = DEFAULT_SETTLE_RATIO_THRESHOLD,
    settle_delay_sec: float = DEFAULT_SETTLE_DELAY_SEC,
    max_side: int = DEFAULT_MAX_SIDE,
    icon_conf: float = DEFAULT_ICON_CONF,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
    vl_max_side: int = DEFAULT_VL_MAX_SIDE,
    runner_max_elements: int = DEFAULT_RUNNER_MAX_ELEMENTS,
    vl_image_format: str = DEFAULT_VL_IMAGE_FORMAT,
    vl_fallback_image_format: str = DEFAULT_VL_FALLBACK_IMAGE_FORMAT,
    vl_webp_quality: int = DEFAULT_VL_WEBP_QUALITY,
    vl_jpeg_quality: int = DEFAULT_VL_JPEG_QUALITY,
    runner_include_screenshot: bool = DEFAULT_RUNNER_INCLUDE_SCREENSHOT,
) -> CaseExecutionRequest:
    patch = runtime_patch or RuntimeOverridePatch(
        max_steps=max_steps,
        max_seconds=max_seconds,
        interval=interval,
        settle_timeout=settle_timeout,
        initial_ready_timeout_sec=initial_ready_timeout_sec,
        settle_mode=settle_mode,
        settle_ocr_only=settle_ocr_only,
        settle_ratio_threshold=settle_ratio_threshold,
        settle_delay_sec=settle_delay_sec,
        max_side=max_side,
        icon_conf=icon_conf,
        max_tokens=max_tokens,
        temperature=temperature,
        vl_max_side=vl_max_side,
        runner_max_elements=runner_max_elements,
        vl_image_format=vl_image_format,
        vl_fallback_image_format=vl_fallback_image_format,
        vl_webp_quality=vl_webp_quality,
        vl_jpeg_quality=vl_jpeg_quality,
        runner_include_screenshot=runner_include_screenshot,
    )
    return CaseExecutionRequest(
        plan_id=plan_id,
        case=case,
        app_id=app_id,
        app_target=app_target,
        device_ref=device_ref,
        artifact_path=artifact_path,
        assets_root=assets_root,
        runtime_overrides=build_runtime_overrides(runtime_patch=patch),
    )


def build_runtime_overrides(
    runtime_patch: RuntimeOverridePatch | None = None,
    *,
    max_steps: int | None = None,
    max_seconds: float | None = None,
    interval: float | None = None,
    settle_timeout: float | None = None,
    initial_ready_timeout_sec: float | None = None,
    settle_mode: str | None = None,
    settle_ocr_only: bool | None = None,
    settle_ratio_threshold: float | None = None,
    settle_delay_sec: float | None = None,
    max_side: int | None = None,
    icon_conf: float | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    vl_max_side: int | None = None,
    runner_max_elements: int | None = None,
    vl_image_format: str | None = None,
    vl_fallback_image_format: str | None = None,
    vl_webp_quality: int | None = None,
    vl_jpeg_quality: int | None = None,
    runner_include_screenshot: bool | None = None,
    include_defaults: bool = True,
) -> dict[str, RuntimeOverrideValue]:
    patch = runtime_patch or RuntimeOverridePatch(
        max_steps=max_steps,
        max_seconds=max_seconds,
        interval=interval,
        settle_timeout=settle_timeout,
        initial_ready_timeout_sec=initial_ready_timeout_sec,
        settle_mode=settle_mode,
        settle_ocr_only=settle_ocr_only,
        settle_ratio_threshold=settle_ratio_threshold,
        settle_delay_sec=settle_delay_sec,
        max_side=max_side,
        icon_conf=icon_conf,
        max_tokens=max_tokens,
        temperature=temperature,
        vl_max_side=vl_max_side,
        runner_max_elements=runner_max_elements,
        vl_image_format=vl_image_format,
        vl_fallback_image_format=vl_fallback_image_format,
        vl_webp_quality=vl_webp_quality,
        vl_jpeg_quality=vl_jpeg_quality,
        runner_include_screenshot=runner_include_screenshot,
    )
    overrides = patch.to_override_dict()
    if not include_defaults:
        return overrides
    defaults: dict[str, RuntimeOverrideValue] = MUNK_CODE_DEFAULTS.runtime.as_runtime_overrides()
    defaults.update(overrides)
    return defaults


def build_runtime_overrides_from_config(runtime_config: ResolvedRuntimeConfig) -> dict[str, RuntimeOverrideValue]:
    return build_runtime_overrides(runtime_patch=runtime_config.to_patch())


def build_runtime_overrides_for_cli(
    resolved_config: ResolvedConfig,
    *,
    max_steps: int | None = None,
    max_seconds: float | None = None,
    interval: float | None = None,
    settle_timeout: float | None = None,
    initial_ready_timeout_sec: float | None = None,
    settle_mode: str | None = None,
    settle_ocr_only: bool | None = None,
    settle_ratio_threshold: float | None = None,
    settle_delay_sec: float | None = None,
    max_side: int | None = None,
    icon_conf: float | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    vl_max_side: int | None = None,
    runner_max_elements: int | None = None,
    vl_image_format: str | None = None,
    vl_fallback_image_format: str | None = None,
    vl_webp_quality: int | None = None,
    vl_jpeg_quality: int | None = None,
    runner_include_screenshot: bool | None = None,
) -> dict[str, RuntimeOverrideValue]:
    resolved_runtime_config = resolve_runtime_config(resolved_config.config)
    overrides = build_runtime_overrides_from_config(resolved_runtime_config)
    overrides.update(build_runtime_overrides(
        runtime_patch=RuntimeOverridePatch(
            max_steps=max_steps,
            max_seconds=max_seconds,
            interval=interval,
            settle_timeout=settle_timeout,
            initial_ready_timeout_sec=initial_ready_timeout_sec,
            settle_mode=settle_mode,
            settle_ocr_only=settle_ocr_only,
            settle_ratio_threshold=settle_ratio_threshold,
            settle_delay_sec=settle_delay_sec,
            max_side=max_side,
            icon_conf=icon_conf,
            max_tokens=max_tokens,
            temperature=temperature,
            vl_max_side=vl_max_side,
            runner_max_elements=runner_max_elements,
            vl_image_format=vl_image_format,
            vl_fallback_image_format=vl_fallback_image_format,
            vl_webp_quality=vl_webp_quality,
            vl_jpeg_quality=vl_jpeg_quality,
            runner_include_screenshot=runner_include_screenshot,
        ),
        include_defaults=False,
    ))
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
