from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AgentRole = Literal["plan", "runner", "judge", "review", "analysis", "optimize", "knowledge"]
LLMProviderKind = Literal["openai_compatible", "gemini"]
OutputStrategy = Literal["auto", "prompted"]


class OpenAICompatibleSection(BaseModel):
    base_url: str = Field(
        ...,
        description="API root including /v1, e.g. http://127.0.0.1:11434/v1",
    )
    api_key: str | None = None
    model: str = Field(..., description="Vision-capable chat model id")
    timeout_sec: float = 120.0
    extra_headers: dict[str, str] = Field(default_factory=dict)
    output_strategy: OutputStrategy = "auto"
    thinking: bool | None = None


class GeminiSection(BaseModel):
    model: str = Field(..., description="Gemini model id, e.g. gemini-2.5-flash")
    api_key: str | None = None
    vertexai: bool = False
    project: str | None = None
    location: str | None = None
    base_url: str | None = None
    timeout_sec: float = 120.0


class AgentModelConfig(BaseModel):
    provider: LLMProviderKind | None = None
    openai_compatible: OpenAICompatibleSection | None = None
    gemini: GeminiSection | None = None


class AgentOpenAICompatibleConfig(AgentModelConfig):
    """Backward-compatible alias for legacy call sites."""


class MunkAgentsConfig(BaseModel):
    plan: AgentModelConfig | None = None
    runner: AgentModelConfig | None = None
    judge: AgentModelConfig | None = None
    review: AgentModelConfig | None = None
    analysis: AgentModelConfig | None = None
    optimize: AgentModelConfig | None = None
    knowledge: AgentModelConfig | None = None


class PerceptionConfig(BaseModel):
    provider: str | None = None
    cache_dir: str | None = None
    extra_options: dict[str, str] = Field(default_factory=dict)


class ProxyConfig(BaseModel):
    enabled: bool = False
    url: str | None = None
    no_proxy: list[str] = Field(default_factory=list)


class RuntimeConfig(BaseModel):
    max_tokens: int | None = None
    temperature: float | None = None
    max_steps: int | None = None
    max_seconds: float | None = None
    interval: float | None = None
    settle_timeout: float | None = None
    max_side: int | None = None
    vl_max_side: int | None = None
    icon_conf: float | None = None


class OrchestrationConfig(BaseModel):
    max_retry_attempts: int | None = Field(default=None, ge=0)
    allow_retry_on_failed: bool | None = None
    allow_retry_on_inconclusive: bool | None = None
    escalate_after_max_attempts: bool | None = None


class MunkConfig(BaseModel):
    provider: LLMProviderKind = "openai_compatible"
    openai_compatible: OpenAICompatibleSection | None = None
    gemini: GeminiSection | None = None
    agents: MunkAgentsConfig | None = None
    perception: PerceptionConfig | None = None
    proxy: ProxyConfig | None = None
    runtime: RuntimeConfig | None = None
    orchestration: OrchestrationConfig | None = None
