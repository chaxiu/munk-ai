import type { StringMapEntry } from '@/shared/lib/stringMapForm'

export type ProviderKind = 'openai_compatible' | 'gemini'
export type OutputStrategy = 'auto' | 'prompted'
export type SettleMode = 'strict' | 'ratio' | 'delay'
export type ThinkingMode = 'default' | 'enabled' | 'disabled'
export type RoleName = 'plan' | 'runner' | 'judge' | 'review' | 'analysis'

export type OpenAIProviderFieldKey
  = 'base_url'
  | 'model'
  | 'timeout_sec'
  | 'api_key'
  | 'extra_headers_json'
  | 'output_strategy'
  | 'thinking_mode'

export type GeminiProviderFieldKey
  = 'model'
  | 'api_key'
  | 'timeout_sec'
  | 'credentials_path'
  | 'base_url'
  | 'project'
  | 'location'

export type ProviderFieldKeyByKind = {
  openai_compatible: OpenAIProviderFieldKey
  gemini: GeminiProviderFieldKey
}

export type ProviderFieldKey = ProviderFieldKeyByKind[ProviderKind]

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
  credentials_path: string
  base_url: string
  timeout_sec: string
}

export type ProviderSectionFormByKind = {
  openai_compatible: OpenAISectionForm
  gemini: GeminiSectionForm
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
  settle_mode: SettleMode
  settle_ocr_only: boolean
  settle_ratio_threshold: string
  settle_delay_sec: string
  max_side: string
  vl_max_side: string
  icon_conf: string
  runner_include_screenshot: boolean
}

export type ProxyConfigForm = {
  enabled: boolean
  url: string
  no_proxy_text: string
}

export type IOSBridgeForm = {
  sudo_enabled: boolean
  sudo_password: string
  sudo_password_configured: boolean
}

export type HttpBaseFormItem = {
  name: string
  url: string
  headers: StringMapEntry[]
}

export type TestEnvForm = {
  bases: HttpBaseFormItem[]
  allowed_exec_text: string
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
  ios_bridge: IOSBridgeForm
  test_env: TestEnvForm
  runtime: RuntimeForm
  orchestration: OrchestrationForm
}

export type OrchestrationData = {
  max_retry_attempts?: number | null
  allow_retry_on_failed?: boolean | null
  allow_retry_on_inconclusive?: boolean | null
  escalate_after_max_attempts?: boolean | null
}

export type ProviderFieldMeta = {
  labelKey: string
  descriptionKey: string
  secret?: boolean
  requiredWhenActive?: boolean
}

export const ROLE_NAMES: RoleName[] = ['plan', 'runner', 'judge', 'review', 'analysis']
