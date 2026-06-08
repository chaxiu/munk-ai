import type { SettingsConfigData, SettingsConfigUpsertRequest } from '@/shared/api/settings'

export type ProviderKind = 'openai_compatible' | 'gemini'
export type OutputStrategy = 'auto' | 'prompted'
export type ThinkingMode = 'default' | 'enabled' | 'disabled'
export type RoleName = 'plan' | 'runner' | 'judge' | 'review' | 'analysis'

export type OpenAISectionForm = {
  configured: boolean
  base_url: string
  api_key: string
  api_key_configured: boolean
  model: string
  timeout_sec: string
  extra_headers_json: string
  output_strategy: OutputStrategy
  thinking_mode: ThinkingMode
}

export type GeminiSectionForm = {
  configured: boolean
  model: string
  api_key: string
  api_key_configured: boolean
  // Compatibility-only fields kept for round-trip with existing config.
  vertexai: boolean
  project: string
  location: string
  base_url: string
  timeout_sec: string
}

export type AgentForm = {
  enabled: boolean
  provider: ProviderKind | ''
  openai_compatible: OpenAISectionForm
  gemini: GeminiSectionForm
}

export type RuntimeForm = {
  max_tokens: string
  temperature: string
  max_steps: string
  max_seconds: string
  interval: string
  settle_timeout: string
  max_side: string
  vl_max_side: string
  icon_conf: string
}

export type ProxyConfigForm = {
  enabled: boolean
  url: string
  no_proxy_text: string
}

export type OrchestrationForm = {
  max_retry_attempts: string
  allow_retry_on_failed: boolean
  allow_retry_on_inconclusive: boolean
  escalate_after_max_attempts: boolean
}

export type SettingsFormState = {
  config_path: string
  file_exists: boolean
  provider: ProviderKind
  openai_compatible: OpenAISectionForm
  gemini: GeminiSectionForm
  agents: Record<RoleName, AgentForm>
  proxy: ProxyConfigForm
  runtime: RuntimeForm
  orchestration: OrchestrationForm
}

type OrchestrationData = {
  max_retry_attempts?: number | null
  allow_retry_on_failed?: boolean | null
  allow_retry_on_inconclusive?: boolean | null
  escalate_after_max_attempts?: boolean | null
}

const ROLE_NAMES: RoleName[] = ['plan', 'runner', 'judge', 'review', 'analysis']

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
    max_side: '',
    vl_max_side: '',
    icon_conf: '',
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

export function createEmptySettingsForm(): SettingsFormState {
  return {
    config_path: '',
    file_exists: false,
    provider: 'openai_compatible',
    openai_compatible: createEmptyOpenAISection(),
    gemini: createEmptyGeminiSection(),
    agents: {
      plan: createEmptyAgentForm(),
      runner: createEmptyAgentForm(),
      judge: createEmptyAgentForm(),
      review: createEmptyAgentForm(),
      analysis: createEmptyAgentForm(),
    },
    proxy: createEmptyProxyConfigForm(),
    runtime: createEmptyRuntimeForm(),
    orchestration: createEmptyOrchestrationForm(),
  }
}

export function buildSettingsForm(data: SettingsConfigData): SettingsFormState {
  const next = createEmptySettingsForm()
  const openai = data.openai_compatible ?? {
    configured: false,
    base_url: null,
    api_key: null,
    api_key_configured: false,
    model: null,
    timeout_sec: null,
    extra_headers: {},
    output_strategy: 'auto' as const,
    thinking: null,
  }
  const gemini = data.gemini ?? {
    configured: false,
    model: null,
    api_key: null,
    api_key_configured: false,
    vertexai: false,
    project: null,
    location: null,
    base_url: null,
    timeout_sec: null,
  }
  const agents = data.agents ?? {}
  const proxy = data.proxy ?? {
    enabled: false,
    url: null,
    no_proxy: [],
  }
  const runtime = data.runtime ?? {}
  const orchestration = (data.orchestration ?? {
    max_retry_attempts: 0,
    allow_retry_on_failed: true,
    allow_retry_on_inconclusive: true,
    escalate_after_max_attempts: false,
  }) as OrchestrationData
  next.config_path = data.config_path
  next.file_exists = data.file_exists
  next.provider = data.provider === 'gemini' ? 'gemini' : 'openai_compatible'
  next.openai_compatible = {
    configured: openai.configured,
    base_url: openai.base_url ?? '',
    api_key: '',
    api_key_configured: openai.api_key_configured,
    model: openai.model ?? '',
    timeout_sec: toText(openai.timeout_sec),
    extra_headers_json: JSON.stringify(openai.extra_headers ?? {}, null, 2),
    output_strategy: openai.output_strategy === 'prompted' ? 'prompted' : 'auto',
    thinking_mode: toThinkingMode(openai.thinking),
  }
  next.gemini = {
    configured: gemini.configured,
    model: gemini.model ?? '',
    api_key: '',
    api_key_configured: gemini.api_key_configured,
    vertexai: gemini.vertexai ?? false,
    project: gemini.project ?? '',
    location: gemini.location ?? '',
    base_url: gemini.base_url ?? '',
    timeout_sec: toText(gemini.timeout_sec),
  }
  for (const role of ROLE_NAMES) {
    const roleData = agents[role] ?? {
      enabled: false,
      provider: null,
      openai_compatible: undefined,
      gemini: undefined,
    }
    const roleOpenAI = roleData.openai_compatible ?? {
      configured: false,
      base_url: null,
      api_key: null,
      api_key_configured: false,
      model: null,
      timeout_sec: null,
      extra_headers: {},
      output_strategy: 'auto' as const,
      thinking: null,
    }
    const roleGemini = roleData.gemini ?? {
      configured: false,
      model: null,
      api_key: null,
      api_key_configured: false,
      vertexai: false,
      project: null,
      location: null,
      base_url: null,
      timeout_sec: null,
    }
    const inferredProvider = inferAgentProvider(roleData.provider, roleOpenAI.configured, roleGemini.configured)
    next.agents[role] = {
      enabled: Boolean(roleData.enabled || inferredProvider),
      provider: inferredProvider,
      openai_compatible: {
        configured: roleOpenAI.configured,
        base_url: roleOpenAI.base_url ?? '',
        api_key: '',
        api_key_configured: roleOpenAI.api_key_configured,
        model: roleOpenAI.model ?? '',
        timeout_sec: toText(roleOpenAI.timeout_sec),
        extra_headers_json: JSON.stringify(roleOpenAI.extra_headers ?? {}, null, 2),
        output_strategy: roleOpenAI.output_strategy === 'prompted' ? 'prompted' : 'auto',
        thinking_mode: toThinkingMode(roleOpenAI.thinking),
      },
      gemini: {
        configured: roleGemini.configured,
        model: roleGemini.model ?? '',
        api_key: '',
        api_key_configured: roleGemini.api_key_configured,
        vertexai: roleGemini.vertexai ?? false,
        project: roleGemini.project ?? '',
        location: roleGemini.location ?? '',
        base_url: roleGemini.base_url ?? '',
        timeout_sec: toText(roleGemini.timeout_sec),
      },
    }
  }
  next.proxy = {
    enabled: proxy.enabled ?? false,
    url: proxy.url ?? '',
    no_proxy_text: formatLineList(proxy.no_proxy ?? []),
  }
  next.runtime = {
    max_tokens: toText(runtime.max_tokens),
    temperature: toText(runtime.temperature),
    max_steps: toText(runtime.max_steps),
    max_seconds: toText(runtime.max_seconds),
    interval: toText(runtime.interval),
    settle_timeout: toText(runtime.settle_timeout),
    max_side: toText(runtime.max_side),
    vl_max_side: toText(runtime.vl_max_side),
    icon_conf: toText(runtime.icon_conf),
  }
  next.orchestration = {
    max_retry_attempts: toText(orchestration.max_retry_attempts),
    allow_retry_on_failed: orchestration.allow_retry_on_failed ?? true,
    allow_retry_on_inconclusive: orchestration.allow_retry_on_inconclusive ?? true,
    escalate_after_max_attempts: orchestration.escalate_after_max_attempts ?? false,
  }
  return next
}

export function buildSettingsRequest(form: SettingsFormState): SettingsConfigUpsertRequest {
  return {
    provider: form.provider,
    openai_compatible: {
      configured: form.openai_compatible.configured,
      base_url: emptyToNull(form.openai_compatible.base_url),
      api_key: emptyToNull(form.openai_compatible.api_key),
      api_key_configured: form.openai_compatible.api_key_configured,
      model: emptyToNull(form.openai_compatible.model),
      timeout_sec: parseNumber(form.openai_compatible.timeout_sec),
      extra_headers: parseHeaders(form.openai_compatible.extra_headers_json),
      output_strategy: form.openai_compatible.output_strategy,
      thinking: fromThinkingMode(form.openai_compatible.thinking_mode),
    },
    gemini: {
      configured: form.gemini.configured,
      model: emptyToNull(form.gemini.model),
      api_key: emptyToNull(form.gemini.api_key),
      api_key_configured: form.gemini.api_key_configured,
      vertexai: form.gemini.vertexai,
      project: emptyToNull(form.gemini.project),
      location: emptyToNull(form.gemini.location),
      base_url: emptyToNull(form.gemini.base_url),
      timeout_sec: parseNumber(form.gemini.timeout_sec),
    },
    agents: {
      plan: buildAgentRequest(form.agents.plan),
      runner: buildAgentRequest(form.agents.runner),
      judge: buildAgentRequest(form.agents.judge),
      review: buildAgentRequest(form.agents.review),
      analysis: buildAgentRequest(form.agents.analysis),
    },
    proxy: {
      enabled: form.proxy.enabled,
      url: emptyToNull(form.proxy.url),
      no_proxy: parseLineList(form.proxy.no_proxy_text),
    },
    runtime: {
      max_tokens: parseInteger(form.runtime.max_tokens),
      temperature: parseNumber(form.runtime.temperature),
      max_steps: parseInteger(form.runtime.max_steps),
      max_seconds: parseNumber(form.runtime.max_seconds),
      interval: parseNumber(form.runtime.interval),
      settle_timeout: parseNumber(form.runtime.settle_timeout),
      max_side: parseInteger(form.runtime.max_side),
      vl_max_side: parseInteger(form.runtime.vl_max_side),
      icon_conf: parseNumber(form.runtime.icon_conf),
    },
    orchestration: {
      max_retry_attempts: parseInteger(form.orchestration.max_retry_attempts),
      allow_retry_on_failed: form.orchestration.allow_retry_on_failed,
      allow_retry_on_inconclusive: form.orchestration.allow_retry_on_inconclusive,
      escalate_after_max_attempts: form.orchestration.escalate_after_max_attempts,
    },
  } as SettingsConfigUpsertRequest
}

function buildAgentRequest(agent: AgentForm): NonNullable<SettingsConfigUpsertRequest['agents']>[RoleName] {
  return {
    enabled: agent.enabled,
    provider: agent.provider || null,
    openai_compatible: {
      configured: agent.openai_compatible.configured,
      base_url: emptyToNull(agent.openai_compatible.base_url),
      api_key: emptyToNull(agent.openai_compatible.api_key),
      api_key_configured: agent.openai_compatible.api_key_configured,
      model: emptyToNull(agent.openai_compatible.model),
      timeout_sec: parseNumber(agent.openai_compatible.timeout_sec),
      extra_headers: parseHeaders(agent.openai_compatible.extra_headers_json),
      output_strategy: agent.openai_compatible.output_strategy,
      thinking: fromThinkingMode(agent.openai_compatible.thinking_mode),
    },
    gemini: {
      configured: agent.gemini.configured,
      model: emptyToNull(agent.gemini.model),
      api_key: emptyToNull(agent.gemini.api_key),
      api_key_configured: agent.gemini.api_key_configured,
      vertexai: agent.gemini.vertexai,
      project: emptyToNull(agent.gemini.project),
      location: emptyToNull(agent.gemini.location),
      base_url: emptyToNull(agent.gemini.base_url),
      timeout_sec: parseNumber(agent.gemini.timeout_sec),
    },
  }
}

export function parseHeaders(text: string): Record<string, string> {
  const trimmed = text.trim()
  if (!trimmed) {
    return {}
  }
  const parsed = JSON.parse(trimmed) as unknown
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('extra_headers must be a JSON object')
  }
  const result: Record<string, string> = {}
  for (const [key, value] of Object.entries(parsed as Record<string, unknown>)) {
    if (typeof value !== 'string') {
      throw new Error('extra_headers values must be strings')
    }
    result[key] = value
  }
  return result
}

export function emptyToNull(value: string): string | null {
  const normalized = value.trim()
  return normalized ? normalized : null
}

export function parseLineList(value: string): string[] {
  return value
    .split('\n')
    .map(item => item.trim())
    .filter(Boolean)
}

function parseNumber(value: string): number | null {
  const normalized = value.trim()
  if (!normalized) {
    return null
  }
  const parsed = Number(normalized)
  if (Number.isNaN(parsed)) {
    throw new Error(`invalid number: ${value}`)
  }
  return parsed
}

function parseInteger(value: string): number | null {
  const parsed = parseNumber(value)
  if (parsed === null) {
    return null
  }
  if (!Number.isInteger(parsed)) {
    throw new Error(`invalid integer: ${value}`)
  }
  return parsed
}

function toText(value: number | null | undefined): string {
  return value === null || value === undefined ? '' : String(value)
}

function formatLineList(values: string[] | null | undefined): string {
  if (!values?.length) {
    return ''
  }
  return values.join('\n')
}

function toThinkingMode(value: boolean | null | undefined): ThinkingMode {
  if (value === true) {
    return 'enabled'
  }
  if (value === false) {
    return 'disabled'
  }
  return 'default'
}

function fromThinkingMode(value: ThinkingMode): boolean | null {
  if (value === 'enabled') {
    return true
  }
  if (value === 'disabled') {
    return false
  }
  return null
}

function inferAgentProvider(
  provider: unknown,
  openaiConfigured: boolean,
  geminiConfigured: boolean,
): ProviderKind | '' {
  if (provider === 'openai_compatible' || provider === 'gemini') {
    return provider
  }
  if (openaiConfigured && !geminiConfigured) {
    return 'openai_compatible'
  }
  if (geminiConfigured && !openaiConfigured) {
    return 'gemini'
  }
  return ''
}
