import type { SettingsConfigData, SettingsConfigUpsertRequest } from '@/shared/api/settings'

import type {
  AgentForm,
  GeminiSectionForm,
  IOSBridgeForm,
  OpenAISectionForm,
  OrchestrationData,
  OrchestrationForm,
  ProviderKind,
  ProxyConfigForm,
  RoleName,
  RuntimeForm,
  SettingsFormState,
} from './settingsFormTypes'
import { ROLE_NAMES } from './settingsFormTypes'
import { isProviderSectionConfigured } from './settingsProviderConfig'
import {
  emptyToNull,
  formatLineList,
  fromThinkingMode,
  inferAgentProvider,
  parseHeaders,
  parseInteger,
  parseLineList,
  parseNumber,
  toSettleMode,
  toText,
  toThinkingMode,
} from './settingsValueUtils'

type OpenAIEditor = NonNullable<SettingsConfigData['openai_compatible']>
type GeminiEditor = NonNullable<SettingsConfigData['gemini']>
type AgentEditor = NonNullable<NonNullable<SettingsConfigData['agents']>[RoleName]>
type ProxyEditor = NonNullable<SettingsConfigData['proxy']>
type IOSBridgeEditor = NonNullable<SettingsConfigData['ios_bridge']>
type RuntimeEditor = NonNullable<SettingsConfigData['runtime']>
type AgentRequest = NonNullable<SettingsConfigUpsertRequest['agents']>[RoleName]
type OpenAIRequest = NonNullable<SettingsConfigUpsertRequest['openai_compatible']>
type GeminiRequest = NonNullable<SettingsConfigUpsertRequest['gemini']>

const EMPTY_OPENAI_EDITOR: OpenAIEditor = {
  configured: false,
  base_url: null,
  api_key: null,
  api_key_configured: false,
  model: null,
  timeout_sec: null,
  extra_headers: {},
  output_strategy: 'auto',
  thinking: null,
}

const EMPTY_GEMINI_EDITOR: GeminiEditor = {
  configured: false,
  model: null,
  api_key: null,
  api_key_configured: false,
  vertexai: false,
  project: null,
  location: null,
  credentials_path: null,
  base_url: null,
  timeout_sec: null,
}

const EMPTY_AGENT_EDITOR: AgentEditor = {
  enabled: false,
  provider: null,
  openai_compatible: undefined,
  gemini: undefined,
}

const EMPTY_PROXY_EDITOR: ProxyEditor = {
  enabled: false,
  url: null,
  no_proxy: [],
}

const EMPTY_IOS_BRIDGE_EDITOR: IOSBridgeEditor = {
  sudo_enabled: false,
  sudo_password: null,
}

const EMPTY_ORCHESTRATION_EDITOR: OrchestrationData = {
  max_retry_attempts: 0,
  allow_retry_on_failed: true,
  allow_retry_on_inconclusive: true,
  escalate_after_max_attempts: false,
}

export function createEmptyOpenAISection(): OpenAISectionForm {
  return {
    configured: false,
    base_url: '',
    api_key: '',
    api_key_configured: false,
    model: '',
    timeout_sec: '',
    extra_headers_json: '{}',
    output_strategy: 'auto',
    thinking_mode: 'default',
  }
}

export function createEmptyGeminiSection(): GeminiSectionForm {
  return {
    configured: false,
    model: '',
    api_key: '',
    api_key_configured: false,
    vertexai: false,
    project: '',
    location: '',
    credentials_path: '',
    base_url: '',
    timeout_sec: '',
  }
}

export function createEmptyAgentForm(): AgentForm {
  return {
    enabled: false,
    provider: '',
    openai_compatible: createEmptyOpenAISection(),
    gemini: createEmptyGeminiSection(),
  }
}

export function createEmptyRuntimeForm(): RuntimeForm {
  return {
    max_tokens: '',
    temperature: '',
    max_steps: '',
    max_seconds: '',
    interval: '',
    settle_timeout: '',
    settle_mode: 'strict',
    settle_ocr_only: false,
    settle_ratio_threshold: '',
    settle_delay_sec: '',
    max_side: '',
    vl_max_side: '',
    icon_conf: '',
    runner_include_screenshot: false,
  }
}

export function createEmptyProxyConfigForm(): ProxyConfigForm {
  return {
    enabled: false,
    url: '',
    no_proxy_text: '',
  }
}

export function createEmptyOrchestrationForm(): OrchestrationForm {
  return {
    max_retry_attempts: '0',
    allow_retry_on_failed: true,
    allow_retry_on_inconclusive: true,
    escalate_after_max_attempts: false,
  }
}

export function createEmptyIOSBridgeForm(): IOSBridgeForm {
  return {
    sudo_enabled: false,
    sudo_password: '',
  }
}

export function createEmptySettingsForm(): SettingsFormState {
  return {
    config_path: '',
    file_exists: false,
    provider: 'openai_compatible',
    openai_compatible: createEmptyOpenAISection(),
    gemini: createEmptyGeminiSection(),
    agents: createEmptyAgentsForm(),
    proxy: createEmptyProxyConfigForm(),
    ios_bridge: createEmptyIOSBridgeForm(),
    runtime: createEmptyRuntimeForm(),
    orchestration: createEmptyOrchestrationForm(),
  }
}

export function buildSettingsForm(data: SettingsConfigData): SettingsFormState {
  return {
    ...createEmptySettingsForm(),
    config_path: data.config_path,
    file_exists: data.file_exists,
    provider: data.provider === 'gemini' ? 'gemini' : 'openai_compatible',
    openai_compatible: buildOpenAISectionForm(data.openai_compatible),
    gemini: buildGeminiSectionForm(data.gemini),
    agents: buildAgentsForm(data.agents),
    proxy: buildProxyForm(data.proxy),
    ios_bridge: buildIOSBridgeForm(data.ios_bridge),
    runtime: buildRuntimeForm(data.runtime),
    orchestration: buildOrchestrationForm(data.orchestration),
  }
}

export function buildSettingsRequest(form: SettingsFormState): SettingsConfigUpsertRequest {
  return {
    provider: form.provider,
    openai_compatible: buildOpenAISectionRequest(form.openai_compatible),
    gemini: buildGeminiSectionRequest(form.gemini),
    agents: buildAgentsRequest(form.agents),
    proxy: {
      enabled: form.proxy.enabled,
      url: emptyToNull(form.proxy.url),
      no_proxy: parseLineList(form.proxy.no_proxy_text),
    },
    ios_bridge: {
      sudo_enabled: form.ios_bridge.sudo_enabled,
      sudo_password: emptyToNull(form.ios_bridge.sudo_password),
    },
    runtime: {
      max_tokens: parseInteger(form.runtime.max_tokens),
      temperature: parseNumber(form.runtime.temperature),
      max_steps: parseInteger(form.runtime.max_steps),
      max_seconds: parseNumber(form.runtime.max_seconds),
      interval: parseNumber(form.runtime.interval),
      settle_timeout: parseNumber(form.runtime.settle_timeout),
      settle_mode: form.runtime.settle_mode,
      settle_ocr_only: form.runtime.settle_ocr_only,
      settle_ratio_threshold: parseNumber(form.runtime.settle_ratio_threshold),
      settle_delay_sec: parseNumber(form.runtime.settle_delay_sec),
      max_side: parseInteger(form.runtime.max_side),
      vl_max_side: parseInteger(form.runtime.vl_max_side),
      icon_conf: parseNumber(form.runtime.icon_conf),
      runner_include_screenshot: form.runtime.runner_include_screenshot,
    },
    orchestration: {
      max_retry_attempts: parseInteger(form.orchestration.max_retry_attempts) ?? 0,
      allow_retry_on_failed: form.orchestration.allow_retry_on_failed,
      allow_retry_on_inconclusive: form.orchestration.allow_retry_on_inconclusive,
      escalate_after_max_attempts: form.orchestration.escalate_after_max_attempts,
    },
  }
}

function buildOpenAISectionForm(section?: OpenAIEditor): OpenAISectionForm {
  const source = section ?? EMPTY_OPENAI_EDITOR
  return {
    configured: source.configured,
    base_url: source.base_url ?? '',
    api_key: '',
    api_key_configured: source.api_key_configured,
    model: source.model ?? '',
    timeout_sec: toText(source.timeout_sec),
    extra_headers_json: JSON.stringify(source.extra_headers ?? {}, null, 2),
    output_strategy: source.output_strategy === 'prompted' ? 'prompted' : 'auto',
    thinking_mode: toThinkingMode(source.thinking),
  }
}

function buildGeminiSectionForm(section?: GeminiEditor): GeminiSectionForm {
  const source = section ?? EMPTY_GEMINI_EDITOR
  return {
    configured: source.configured,
    model: source.model ?? '',
    api_key: '',
    api_key_configured: source.api_key_configured,
    vertexai: source.vertexai ?? false,
    project: source.project ?? '',
    location: source.location ?? '',
    credentials_path: source.credentials_path ?? '',
    base_url: source.base_url ?? '',
    timeout_sec: toText(source.timeout_sec),
  }
}

function buildAgentForm(roleData?: AgentEditor): AgentForm {
  const source = roleData ?? EMPTY_AGENT_EDITOR
  const openaiSection = source.openai_compatible ?? EMPTY_OPENAI_EDITOR
  const geminiSection = source.gemini ?? EMPTY_GEMINI_EDITOR
  const provider = inferAgentProvider(source.provider, openaiSection.configured, geminiSection.configured)

  return {
    enabled: Boolean(source.enabled || provider),
    provider,
    openai_compatible: buildOpenAISectionForm(openaiSection),
    gemini: buildGeminiSectionForm(geminiSection),
  }
}

function buildAgentsForm(agents?: SettingsConfigData['agents']): Record<RoleName, AgentForm> {
  return {
    plan: buildAgentForm(agents?.plan),
    runner: buildAgentForm(agents?.runner),
    judge: buildAgentForm(agents?.judge),
    review: buildAgentForm(agents?.review),
    analysis: buildAgentForm(agents?.analysis),
  }
}

function buildProxyForm(proxy?: ProxyEditor): ProxyConfigForm {
  const source = proxy ?? EMPTY_PROXY_EDITOR
  return {
    enabled: source.enabled ?? false,
    url: source.url ?? '',
    no_proxy_text: formatLineList(source.no_proxy ?? []),
  }
}

function buildIOSBridgeForm(iosBridge?: IOSBridgeEditor): IOSBridgeForm {
  const source = iosBridge ?? EMPTY_IOS_BRIDGE_EDITOR
  return {
    sudo_enabled: source.sudo_enabled ?? false,
    sudo_password: source.sudo_password ?? '',
  }
}

function buildRuntimeForm(runtime?: RuntimeEditor): RuntimeForm {
  const source = runtime ?? {}
  return {
    max_tokens: toText(source.max_tokens),
    temperature: toText(source.temperature),
    max_steps: toText(source.max_steps),
    max_seconds: toText(source.max_seconds),
    interval: toText(source.interval),
    settle_timeout: toText(source.settle_timeout),
    settle_mode: toSettleMode(source.settle_mode),
    settle_ocr_only: source.settle_ocr_only ?? false,
    settle_ratio_threshold: toText(source.settle_ratio_threshold),
    settle_delay_sec: toText(source.settle_delay_sec),
    max_side: toText(source.max_side),
    vl_max_side: toText(source.vl_max_side),
    icon_conf: toText(source.icon_conf),
    runner_include_screenshot: source.runner_include_screenshot ?? false,
  }
}

function buildOrchestrationForm(orchestration?: SettingsConfigData['orchestration']): OrchestrationForm {
  const source = orchestration ?? EMPTY_ORCHESTRATION_EDITOR
  return {
    max_retry_attempts: toText(source.max_retry_attempts),
    allow_retry_on_failed: source.allow_retry_on_failed ?? true,
    allow_retry_on_inconclusive: source.allow_retry_on_inconclusive ?? true,
    escalate_after_max_attempts: source.escalate_after_max_attempts ?? false,
  }
}

function buildOpenAISectionRequest(section: OpenAISectionForm): OpenAIRequest {
  return {
    configured: isProviderSectionConfigured('openai_compatible', section),
    base_url: emptyToNull(section.base_url),
    api_key: emptyToNull(section.api_key),
    api_key_configured: section.api_key_configured,
    model: emptyToNull(section.model),
    timeout_sec: parseNumber(section.timeout_sec),
    extra_headers: parseHeaders(section.extra_headers_json),
    output_strategy: section.output_strategy,
    thinking: fromThinkingMode(section.thinking_mode),
  }
}

function buildGeminiSectionRequest(section: GeminiSectionForm): GeminiRequest {
  return {
    configured: isProviderSectionConfigured('gemini', section),
    model: emptyToNull(section.model),
    api_key: emptyToNull(section.api_key),
    api_key_configured: section.api_key_configured,
    vertexai: section.vertexai,
    project: emptyToNull(section.project),
    location: emptyToNull(section.location),
    credentials_path: emptyToNull(section.credentials_path),
    base_url: emptyToNull(section.base_url),
    timeout_sec: parseNumber(section.timeout_sec),
  }
}

function buildAgentRequest(agent: AgentForm): AgentRequest {
  return {
    enabled: agent.enabled,
    provider: agent.provider || null,
    openai_compatible: buildOpenAISectionRequest(agent.openai_compatible),
    gemini: buildGeminiSectionRequest(agent.gemini),
  }
}

function buildAgentsRequest(agents: Record<RoleName, AgentForm>): NonNullable<SettingsConfigUpsertRequest['agents']> {
  return {
    plan: buildAgentRequest(agents.plan),
    runner: buildAgentRequest(agents.runner),
    judge: buildAgentRequest(agents.judge),
    review: buildAgentRequest(agents.review),
    analysis: buildAgentRequest(agents.analysis),
  }
}

function createEmptyAgentsForm(): Record<RoleName, AgentForm> {
  return ROLE_NAMES.reduce<Record<RoleName, AgentForm>>((acc, role) => {
    acc[role] = createEmptyAgentForm()
    return acc
  }, {} as Record<RoleName, AgentForm>)
}
