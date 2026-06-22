import type { SettleMode, ThinkingMode } from './settingsFormTypes'

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

export function parseNumber(value: string): number | null {
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

export function parseInteger(value: string): number | null {
  const parsed = parseNumber(value)
  if (parsed === null) {
    return null
  }
  if (!Number.isInteger(parsed)) {
    throw new Error(`invalid integer: ${value}`)
  }
  return parsed
}

export function toText(value: number | null | undefined): string {
  return value === null || value === undefined ? '' : String(value)
}

export function formatLineList(values: string[] | null | undefined): string {
  if (!values?.length) {
    return ''
  }
  return values.join('\n')
}

export function hasConfiguredExtraHeaders(value: string): boolean {
  const trimmed = value.trim()
  if (!trimmed) {
    return false
  }
  try {
    const parsed = JSON.parse(trimmed) as unknown
    return Boolean(parsed && typeof parsed === 'object' && !Array.isArray(parsed) && Object.keys(parsed).length > 0)
  } catch {
    return true
  }
}

export function toThinkingMode(value: boolean | null | undefined): ThinkingMode {
  if (value === true) {
    return 'enabled'
  }
  if (value === false) {
    return 'disabled'
  }
  return 'default'
}

export function toSettleMode(value: unknown): SettleMode {
  if (value === 'ratio' || value === 'delay') {
    return value
  }
  return 'strict'
}

export function fromThinkingMode(value: ThinkingMode): boolean | null {
  if (value === 'enabled') {
    return true
  }
  if (value === 'disabled') {
    return false
  }
  return null
}

export function inferAgentProvider(
  provider: unknown,
  openaiConfigured: boolean,
  geminiConfigured: boolean,
): 'openai_compatible' | 'gemini' | '' {
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
