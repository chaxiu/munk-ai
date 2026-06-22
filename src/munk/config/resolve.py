from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any, Callable, Mapping, cast

from munk.config.defaults import (
    DEFAULT_ALLOW_RETRY_ON_FAILED,
    DEFAULT_ALLOW_RETRY_ON_INCONCLUSIVE,
    DEFAULT_ESCALATE_AFTER_MAX_ATTEMPTS,
    MUNK_CODE_DEFAULTS,
    DEFAULT_MAX_RETRY_ATTEMPTS,
)
from munk.execution.models import RuntimeOverrideValue
from munk.config.schema import (
    AgentRole,
    GeminiSection,
    LLMProviderKind,
    MunkConfig,
    OpenAICompatibleSection,
    RuntimeConfig,
)
from munk.orchestration import OrchestrationPolicy
from munk.running import runtime_override_specs

ModelConfigSection = OpenAICompatibleSection | GeminiSection


def _optional_int(payload: Mapping[str, object], key: str) -> int | None:
    value = payload.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _optional_float(payload: Mapping[str, object], key: str) -> float | None:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def _optional_str(payload: Mapping[str, object], key: str) -> str | None:
    value = payload.get(key)
    return value if isinstance(value, str) else None


def _optional_bool(payload: Mapping[str, object], key: str) -> bool | None:
    value = payload.get(key)
    return value if isinstance(value, bool) else None


_RuntimeOverrideParser = Callable[[Mapping[str, object], str], RuntimeOverrideValue | None]
_RUNTIME_OVERRIDE_VALUE_PARSERS: dict[str, _RuntimeOverrideParser] = {
    "int": _optional_int,
    "float": _optional_float,
    "bool": _optional_bool,
    "str": _optional_str,
}
_RUNTIME_OVERRIDE_PARSERS_BY_KEY: dict[str, _RuntimeOverrideParser] = {
    spec.key: _RUNTIME_OVERRIDE_VALUE_PARSERS[spec.value_kind]
    for spec in runtime_override_specs()
}


@dataclass(frozen=True)
class ResolvedModelConfig:
    provider: LLMProviderKind
    model: str
    timeout_sec: float
    config_section: ModelConfigSection


@dataclass(frozen=True)
class RuntimeOverridePatch:
    max_tokens: int | None = None
    temperature: float | None = None
    max_steps: int | None = None
    max_seconds: float | None = None
    interval: float | None = None
    settle_timeout: float | None = None
    initial_ready_timeout_sec: float | None = None
    settle_mode: str | None = None
    settle_ocr_only: bool | None = None
    settle_ratio_threshold: float | None = None
    settle_delay_sec: float | None = None
    max_side: int | None = None
    vl_max_side: int | None = None
    runner_max_elements: int | None = None
    vl_image_format: str | None = None
    vl_fallback_image_format: str | None = None
    vl_webp_quality: int | None = None
    vl_jpeg_quality: int | None = None
    icon_conf: float | None = None
    runner_include_screenshot: bool | None = None

    def to_override_dict(self) -> dict[str, RuntimeOverrideValue]:
        return {
            field.name: value
            for field in fields(self)
            if (value := getattr(self, field.name)) is not None
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> "RuntimeOverridePatch":
        values: dict[str, object] = {
            field.name: _RUNTIME_OVERRIDE_PARSERS_BY_KEY[field.name](payload, field.name)
            for field in fields(cls)
        }
        return cast("RuntimeOverridePatch", cls(**cast(Any, values)))

    @classmethod
    def from_runtime_config(cls, runtime: RuntimeConfig | None) -> "RuntimeOverridePatch":
        if runtime is None:
            return cls()
        return cls.from_mapping(runtime.model_dump(exclude_none=True))


@dataclass(frozen=True)
class ResolvedRuntimeConfig:
    max_tokens: int
    temperature: float
    max_steps: int
    max_seconds: float
    interval: float
    settle_timeout: float
    initial_ready_timeout_sec: float
    settle_mode: str
    settle_ocr_only: bool
    settle_ratio_threshold: float
    settle_delay_sec: float
    max_side: int
    vl_max_side: int
    runner_max_elements: int
    vl_image_format: str
    vl_fallback_image_format: str
    vl_webp_quality: int
    vl_jpeg_quality: int
    icon_conf: float
    runner_include_screenshot: bool

    def to_patch(self) -> RuntimeOverridePatch:
        return RuntimeOverridePatch(**asdict(self))


@dataclass(frozen=True)
class ResolvedOrchestrationConfig:
    max_retry_attempts: int
    allow_retry_on_failed: bool
    allow_retry_on_inconclusive: bool
    escalate_after_max_attempts: bool


def resolve_role_model_config(
    config: MunkConfig,
    *,
    role: AgentRole,
) -> ResolvedModelConfig | None:
    agents = getattr(config, "agents", None)
    role_config = getattr(agents, role) if agents is not None else None
    provider = role_config.provider if role_config is not None and role_config.provider is not None else config.provider
    section = _resolve_section_for_provider(
        provider,
        role_openai=role_config.openai_compatible if role_config is not None else None,
        role_gemini=role_config.gemini if role_config is not None else None,
        default_openai=config.openai_compatible,
        default_gemini=config.gemini,
    )
    if section is None:
        return None
    return ResolvedModelConfig(
        provider=provider,
        model=section.model,
        timeout_sec=section.timeout_sec,
        config_section=section,
    )


def resolve_openai_compatible_section(
    config: MunkConfig,
    *,
    role: AgentRole,
) -> OpenAICompatibleSection | None:
    resolved = resolve_role_model_config(config, role=role)
    if resolved is None or resolved.provider != "openai_compatible":
        return None
    if isinstance(resolved.config_section, OpenAICompatibleSection):
        return resolved.config_section
    return None


def resolve_runtime_config(config: MunkConfig) -> ResolvedRuntimeConfig:
    resolved_values = asdict(MUNK_CODE_DEFAULTS.runtime)
    resolved_values.update(RuntimeOverridePatch.from_runtime_config(config.runtime).to_override_dict())
    return ResolvedRuntimeConfig(**resolved_values)


def resolve_orchestration_config(config: MunkConfig) -> ResolvedOrchestrationConfig:
    orchestration = config.orchestration
    return ResolvedOrchestrationConfig(
        max_retry_attempts=(
            orchestration.max_retry_attempts
            if orchestration is not None and orchestration.max_retry_attempts is not None
            else DEFAULT_MAX_RETRY_ATTEMPTS
        ),
        allow_retry_on_failed=(
            orchestration.allow_retry_on_failed
            if orchestration is not None and orchestration.allow_retry_on_failed is not None
            else DEFAULT_ALLOW_RETRY_ON_FAILED
        ),
        allow_retry_on_inconclusive=(
            orchestration.allow_retry_on_inconclusive
            if orchestration is not None and orchestration.allow_retry_on_inconclusive is not None
            else DEFAULT_ALLOW_RETRY_ON_INCONCLUSIVE
        ),
        escalate_after_max_attempts=(
            orchestration.escalate_after_max_attempts
            if orchestration is not None and orchestration.escalate_after_max_attempts is not None
            else DEFAULT_ESCALATE_AFTER_MAX_ATTEMPTS
        ),
    )


def resolve_orchestration_policy(config: MunkConfig) -> OrchestrationPolicy:
    orchestration = resolve_orchestration_config(config)
    return OrchestrationPolicy(
        max_retry_attempts=orchestration.max_retry_attempts,
        retry_on_failed=orchestration.allow_retry_on_failed,
        retry_on_inconclusive=orchestration.allow_retry_on_inconclusive,
        escalate_after_max_attempts=orchestration.escalate_after_max_attempts,
    )


def _resolve_section_for_provider(
    provider: LLMProviderKind,
    *,
    role_openai: OpenAICompatibleSection | None,
    role_gemini: GeminiSection | None,
    default_openai: OpenAICompatibleSection | None,
    default_gemini: GeminiSection | None,
) -> ModelConfigSection | None:
    if provider == "openai_compatible":
        return role_openai or default_openai
    return role_gemini or default_gemini
