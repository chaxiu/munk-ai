from __future__ import annotations

from dataclasses import dataclass, field

from munk.execution.models import RuntimeOverrideValue


@dataclass(frozen=True)
class RuntimeDefaultConfig:
    max_steps: int = 30
    max_seconds: float = 300.0
    interval: float = 0.5
    settle_timeout: float = 10.0
    max_side: int = 1024
    icon_conf: float = 0.12
    max_tokens: int = 8192
    temperature: float = 0.2
    vl_max_side: int = 1024

    def as_runtime_overrides(self) -> dict[str, RuntimeOverrideValue]:
        return {
            "max_steps": self.max_steps,
            "max_seconds": self.max_seconds,
            "interval": self.interval,
            "settle_timeout": self.settle_timeout,
            "max_side": self.max_side,
            "icon_conf": self.icon_conf,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "vl_max_side": self.vl_max_side,
        }


@dataclass(frozen=True)
class OrchestrationDefaultConfig:
    max_retry_attempts: int = 0
    allow_retry_on_failed: bool = True
    allow_retry_on_inconclusive: bool = True
    escalate_after_max_attempts: bool = False


@dataclass(frozen=True)
class InferenceDefaultConfig:
    max_tokens: int
    temperature: float

    def as_model_settings(self) -> dict[str, int | float]:
        return {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }


@dataclass(frozen=True)
class RunnerDefaultConfig(InferenceDefaultConfig):
    top_p: float = 0.9
    max_elements: int = 80
    prompt_max_elements: int = 40
    max_history: int = 6

    def as_model_settings(self) -> dict[str, int | float]:
        settings = super().as_model_settings()
        settings["top_p"] = self.top_p
        return settings


@dataclass(frozen=True)
class PlanAgentDefaultConfig(InferenceDefaultConfig):
    max_cases: int = 8


@dataclass(frozen=True)
class TelemetryDefaultConfig:
    # OSS 源码仅保留 telemetry 默认值；真实 key 通过运行时环境变量注入。
    enabled: bool = True
    posthog_host: str = "https://us.i.posthog.com"
    posthog_api_key: str | None = None
    timeout_sec: float = 2.0


@dataclass(frozen=True)
class MunkCodeDefaults:
    runtime: RuntimeDefaultConfig = field(default_factory=RuntimeDefaultConfig)
    orchestration: OrchestrationDefaultConfig = field(default_factory=OrchestrationDefaultConfig)
    vision_preflight: InferenceDefaultConfig = field(
        default_factory=lambda: InferenceDefaultConfig(max_tokens=512, temperature=0.0)
    )
    runner: RunnerDefaultConfig = field(
        default_factory=lambda: RunnerDefaultConfig(max_tokens=8192, temperature=0.2)
    )
    judge: InferenceDefaultConfig = field(
        default_factory=lambda: InferenceDefaultConfig(max_tokens=8192, temperature=0.0)
    )
    optimize: InferenceDefaultConfig = field(
        default_factory=lambda: InferenceDefaultConfig(max_tokens=8192, temperature=0.0)
    )
    knowledge: InferenceDefaultConfig = field(
        default_factory=lambda: InferenceDefaultConfig(max_tokens=8192, temperature=0.0)
    )
    plan: PlanAgentDefaultConfig = field(
        default_factory=lambda: PlanAgentDefaultConfig(max_tokens=8192, temperature=0.2)
    )
    telemetry: TelemetryDefaultConfig = field(default_factory=TelemetryDefaultConfig)


MUNK_CODE_DEFAULTS = MunkCodeDefaults()


# Backward-compatible aliases for the existing runtime defaults API.
DEFAULT_MAX_STEPS = MUNK_CODE_DEFAULTS.runtime.max_steps
DEFAULT_MAX_SECONDS = MUNK_CODE_DEFAULTS.runtime.max_seconds
DEFAULT_INTERVAL = MUNK_CODE_DEFAULTS.runtime.interval
DEFAULT_SETTLE_TIMEOUT = MUNK_CODE_DEFAULTS.runtime.settle_timeout
DEFAULT_MAX_SIDE = MUNK_CODE_DEFAULTS.runtime.max_side
DEFAULT_ICON_CONF = MUNK_CODE_DEFAULTS.runtime.icon_conf
DEFAULT_MAX_TOKENS = MUNK_CODE_DEFAULTS.runtime.max_tokens
DEFAULT_TEMPERATURE = MUNK_CODE_DEFAULTS.runtime.temperature
DEFAULT_VL_MAX_SIDE = MUNK_CODE_DEFAULTS.runtime.vl_max_side
DEFAULT_MAX_RETRY_ATTEMPTS = MUNK_CODE_DEFAULTS.orchestration.max_retry_attempts
DEFAULT_ALLOW_RETRY_ON_FAILED = MUNK_CODE_DEFAULTS.orchestration.allow_retry_on_failed
DEFAULT_ALLOW_RETRY_ON_INCONCLUSIVE = MUNK_CODE_DEFAULTS.orchestration.allow_retry_on_inconclusive
DEFAULT_ESCALATE_AFTER_MAX_ATTEMPTS = MUNK_CODE_DEFAULTS.orchestration.escalate_after_max_attempts

DEFAULT_VISION_PREFLIGHT_MAX_TOKENS = MUNK_CODE_DEFAULTS.vision_preflight.max_tokens
DEFAULT_VISION_PREFLIGHT_TEMPERATURE = MUNK_CODE_DEFAULTS.vision_preflight.temperature
DEFAULT_RUNNER_MAX_TOKENS = MUNK_CODE_DEFAULTS.runner.max_tokens
DEFAULT_RUNNER_TEMPERATURE = MUNK_CODE_DEFAULTS.runner.temperature
DEFAULT_RUNNER_TOP_P = MUNK_CODE_DEFAULTS.runner.top_p
DEFAULT_RUNNER_MAX_ELEMENTS = MUNK_CODE_DEFAULTS.runner.max_elements
DEFAULT_RUNNER_PROMPT_MAX_ELEMENTS = MUNK_CODE_DEFAULTS.runner.prompt_max_elements
DEFAULT_RUNNER_MAX_HISTORY = MUNK_CODE_DEFAULTS.runner.max_history
DEFAULT_JUDGE_MAX_TOKENS = MUNK_CODE_DEFAULTS.judge.max_tokens
DEFAULT_JUDGE_TEMPERATURE = MUNK_CODE_DEFAULTS.judge.temperature
DEFAULT_OPTIMIZE_MAX_TOKENS = MUNK_CODE_DEFAULTS.optimize.max_tokens
DEFAULT_OPTIMIZE_TEMPERATURE = MUNK_CODE_DEFAULTS.optimize.temperature
DEFAULT_KNOWLEDGE_MAX_TOKENS = MUNK_CODE_DEFAULTS.knowledge.max_tokens
DEFAULT_KNOWLEDGE_TEMPERATURE = MUNK_CODE_DEFAULTS.knowledge.temperature
DEFAULT_PLAN_MAX_TOKENS = MUNK_CODE_DEFAULTS.plan.max_tokens
DEFAULT_PLAN_TEMPERATURE = MUNK_CODE_DEFAULTS.plan.temperature
DEFAULT_PLAN_MAX_CASES = MUNK_CODE_DEFAULTS.plan.max_cases
