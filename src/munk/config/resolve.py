from __future__ import annotations

from dataclasses import dataclass

from munk.config.defaults import (
    DEFAULT_ALLOW_RETRY_ON_FAILED,
    DEFAULT_ALLOW_RETRY_ON_INCONCLUSIVE,
    DEFAULT_ESCALATE_AFTER_MAX_ATTEMPTS,
    DEFAULT_ICON_CONF,
    DEFAULT_INTERVAL,
    DEFAULT_MAX_RETRY_ATTEMPTS,
    DEFAULT_MAX_SECONDS,
    DEFAULT_MAX_SIDE,
    DEFAULT_MAX_STEPS,
    DEFAULT_MAX_TOKENS,
    DEFAULT_SETTLE_TIMEOUT,
    DEFAULT_TEMPERATURE,
    DEFAULT_VL_MAX_SIDE,
)
from munk.config.schema import (
    AgentRole,
    GeminiSection,
    LLMProviderKind,
    MunkConfig,
    OpenAICompatibleSection,
)
from munk.orchestration import OrchestrationPolicy

ModelConfigSection = OpenAICompatibleSection | GeminiSection


@dataclass(frozen=True)
class ResolvedModelConfig:
    provider: LLMProviderKind
    model: str
    timeout_sec: float
    config_section: ModelConfigSection


@dataclass(frozen=True)
class ResolvedRuntimeConfig:
    max_tokens: int
    temperature: float
    max_steps: int
    max_seconds: float
    interval: float
    settle_timeout: float
    max_side: int
    vl_max_side: int
    icon_conf: float


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
    runtime = config.runtime
    return ResolvedRuntimeConfig(
        max_tokens=runtime.max_tokens if runtime is not None and runtime.max_tokens is not None else DEFAULT_MAX_TOKENS,
        temperature=runtime.temperature
        if runtime is not None and runtime.temperature is not None
        else DEFAULT_TEMPERATURE,
        max_steps=runtime.max_steps if runtime is not None and runtime.max_steps is not None else DEFAULT_MAX_STEPS,
        max_seconds=runtime.max_seconds
        if runtime is not None and runtime.max_seconds is not None
        else DEFAULT_MAX_SECONDS,
        interval=runtime.interval if runtime is not None and runtime.interval is not None else DEFAULT_INTERVAL,
        settle_timeout=runtime.settle_timeout
        if runtime is not None and runtime.settle_timeout is not None
        else DEFAULT_SETTLE_TIMEOUT,
        max_side=runtime.max_side if runtime is not None and runtime.max_side is not None else DEFAULT_MAX_SIDE,
        vl_max_side=runtime.vl_max_side
        if runtime is not None and runtime.vl_max_side is not None
        else DEFAULT_VL_MAX_SIDE,
        icon_conf=runtime.icon_conf if runtime is not None and runtime.icon_conf is not None else DEFAULT_ICON_CONF,
    )


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
