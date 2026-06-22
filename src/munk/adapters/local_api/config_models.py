from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from munk.config.schema import LLMProviderKind, OutputStrategy, SettleMode


class OpenAICompatibleSectionEditor(BaseModel):
    model_config = ConfigDict(extra="ignore")

    configured: bool = False
    base_url: str | None = None
    api_key: str | None = None
    api_key_configured: bool = False
    model: str | None = None
    timeout_sec: float | None = None
    extra_headers: dict[str, str] = Field(default_factory=dict)
    output_strategy: OutputStrategy = "auto"
    thinking: bool | None = None


class GeminiSectionEditor(BaseModel):
    model_config = ConfigDict(extra="ignore")

    configured: bool = False
    model: str | None = None
    api_key: str | None = None
    api_key_configured: bool = False
    vertexai: bool = False
    project: str | None = None
    location: str | None = None
    credentials_path: str | None = None
    base_url: str | None = None
    timeout_sec: float | None = None


class AgentConfigEditor(BaseModel):
    model_config = ConfigDict(extra="ignore")

    enabled: bool = False
    provider: LLMProviderKind | None = None
    openai_compatible: OpenAICompatibleSectionEditor = Field(default_factory=OpenAICompatibleSectionEditor)
    gemini: GeminiSectionEditor = Field(default_factory=GeminiSectionEditor)


class SettingsAgentsEditor(BaseModel):
    model_config = ConfigDict(extra="ignore")

    plan: AgentConfigEditor = Field(default_factory=AgentConfigEditor)
    runner: AgentConfigEditor = Field(default_factory=AgentConfigEditor)
    judge: AgentConfigEditor = Field(default_factory=AgentConfigEditor)
    review: AgentConfigEditor = Field(default_factory=AgentConfigEditor)
    analysis: AgentConfigEditor = Field(default_factory=AgentConfigEditor)


class RuntimeConfigEditor(BaseModel):
    model_config = ConfigDict(extra="ignore")

    max_tokens: int | None = None
    temperature: float | None = None
    max_steps: int | None = None
    max_seconds: float | None = None
    interval: float | None = None
    settle_timeout: float | None = None
    settle_mode: SettleMode | None = None
    settle_ocr_only: bool | None = None
    settle_ratio_threshold: float | None = None
    settle_delay_sec: float | None = None
    max_side: int | None = None
    vl_max_side: int | None = None
    icon_conf: float | None = None
    runner_include_screenshot: bool | None = None


class OrchestrationConfigEditor(BaseModel):
    model_config = ConfigDict(extra="ignore")

    max_retry_attempts: int = Field(default=0, ge=0)
    allow_retry_on_failed: bool = True
    allow_retry_on_inconclusive: bool = True
    escalate_after_max_attempts: bool = False


class ProxyConfigEditor(BaseModel):
    model_config = ConfigDict(extra="ignore")

    enabled: bool = False
    url: str | None = None
    no_proxy: list[str] = Field(default_factory=list)


class IOSBridgeConfigEditor(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sudo_enabled: bool = False
    sudo_password: str | None = None


class SettingsConfigUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    provider: LLMProviderKind = "openai_compatible"
    openai_compatible: OpenAICompatibleSectionEditor = Field(default_factory=OpenAICompatibleSectionEditor)
    gemini: GeminiSectionEditor = Field(default_factory=GeminiSectionEditor)
    agents: SettingsAgentsEditor = Field(default_factory=SettingsAgentsEditor)
    proxy: ProxyConfigEditor = Field(default_factory=ProxyConfigEditor)
    ios_bridge: IOSBridgeConfigEditor = Field(default_factory=IOSBridgeConfigEditor)
    runtime: RuntimeConfigEditor = Field(default_factory=RuntimeConfigEditor)
    orchestration: OrchestrationConfigEditor = Field(default_factory=OrchestrationConfigEditor)
