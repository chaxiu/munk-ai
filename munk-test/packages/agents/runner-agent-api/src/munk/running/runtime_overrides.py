from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Literal, Mapping, TypeVar, cast

from munk.execution.models import RuntimeOverrideValue

RuntimeOverrideValueKind = Literal["int", "float", "bool", "str"]
_RuntimeParamsT = TypeVar("_RuntimeParamsT")


@dataclass(frozen=True)
class RuntimeOverrideSpec:
    key: str
    value_kind: RuntimeOverrideValueKind
    allowed_values: tuple[str, ...] | None = None


MANAGED_CONTEXT_OVERRIDE_KEYS = frozenset({"device_ref", "goal", "app_id", "plan_id", "case_id"})

_RUNTIME_OVERRIDE_SPECS: tuple[RuntimeOverrideSpec, ...] = (
    RuntimeOverrideSpec("max_steps", "int"),
    RuntimeOverrideSpec("max_seconds", "float"),
    RuntimeOverrideSpec("interval", "float"),
    RuntimeOverrideSpec("settle_timeout", "float"),
    RuntimeOverrideSpec("initial_ready_timeout_sec", "float"),
    RuntimeOverrideSpec("icon_conf", "float"),
    RuntimeOverrideSpec("temperature", "float"),
    RuntimeOverrideSpec("settle_ratio_threshold", "float"),
    RuntimeOverrideSpec("settle_delay_sec", "float"),
    RuntimeOverrideSpec("max_side", "int"),
    RuntimeOverrideSpec("max_tokens", "int"),
    RuntimeOverrideSpec("vl_max_side", "int"),
    RuntimeOverrideSpec("runner_max_elements", "int"),
    RuntimeOverrideSpec("vl_webp_quality", "int"),
    RuntimeOverrideSpec("vl_jpeg_quality", "int"),
    RuntimeOverrideSpec("vl_image_format", "str", ("webp", "jpeg")),
    RuntimeOverrideSpec("vl_fallback_image_format", "str", ("jpeg",)),
    RuntimeOverrideSpec("settle_mode", "str", ("strict", "ratio", "delay")),
    RuntimeOverrideSpec("settle_ocr_only", "bool"),
    RuntimeOverrideSpec("runner_include_screenshot", "bool"),
)
_RUNTIME_OVERRIDE_SPECS_BY_KEY = {spec.key: spec for spec in _RUNTIME_OVERRIDE_SPECS}


def runtime_override_specs() -> tuple[RuntimeOverrideSpec, ...]:
    return _RUNTIME_OVERRIDE_SPECS


def runtime_override_keys() -> tuple[str, ...]:
    return tuple(spec.key for spec in _RUNTIME_OVERRIDE_SPECS)


def validate_runtime_override(key: str, value: RuntimeOverrideValue) -> RuntimeOverrideValue:
    if key in MANAGED_CONTEXT_OVERRIDE_KEYS:
        raise ValueError(f"{key} is managed by case context and cannot be overridden")
    spec = _RUNTIME_OVERRIDE_SPECS_BY_KEY.get(key)
    if spec is None:
        raise ValueError(f"unsupported runtime override: {key}")
    normalized = _normalize_runtime_override_value(spec, value)
    if spec.allowed_values is not None and normalized not in spec.allowed_values:
        allowed = ", ".join(spec.allowed_values)
        raise ValueError(f"runtime override '{key}' must be one of: {allowed}")
    return normalized


def normalize_runtime_overrides(
    overrides: Mapping[str, RuntimeOverrideValue],
) -> dict[str, RuntimeOverrideValue]:
    return {key: validate_runtime_override(key, value) for key, value in overrides.items()}


def apply_runtime_overrides(
    runtime_params: _RuntimeParamsT,
    overrides: Mapping[str, RuntimeOverrideValue],
) -> _RuntimeParamsT:
    updated = runtime_params
    for key, value in overrides.items():
        updated = cast(
            _RuntimeParamsT,
            replace(cast(Any, updated), **{key: validate_runtime_override(key, value)}),
        )
    return updated


def _normalize_runtime_override_value(
    spec: RuntimeOverrideSpec,
    value: RuntimeOverrideValue,
) -> RuntimeOverrideValue:
    if spec.value_kind == "int":
        return _require_int_override(spec.key, value)
    if spec.value_kind == "float":
        return _require_float_override(spec.key, value)
    if spec.value_kind == "bool":
        return _require_bool_override(spec.key, value)
    return _require_string_override(spec.key, value)


def _require_int_override(key: str, value: RuntimeOverrideValue) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"runtime override '{key}' must be an integer")
    return value


def _require_float_override(key: str, value: RuntimeOverrideValue) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"runtime override '{key}' must be a number")
    return float(value)


def _require_bool_override(key: str, value: RuntimeOverrideValue) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"runtime override '{key}' must be a boolean")
    return value


def _require_string_override(key: str, value: RuntimeOverrideValue) -> str:
    if not isinstance(value, str):
        raise ValueError(f"runtime override '{key}' must be a string")
    return value
