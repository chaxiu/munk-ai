import type { Translate } from './runMapperShared'
import type { OperationEventItem, RunTimelineDetailRow } from './runTimelineTypes'
import { asNumber, asObject, asString, prettifyToken } from './runMapperShared'

export const HISTORICAL_TIMELINE_EVENT_TYPES = new Set([
  'workflow_started',
  'workflow_attempt_started',
  'workflow_attempt_finished',
  'workflow_retry_scheduled',
  'workflow_finished',
  'judge_decision',
])

export const LLM_TIMELINE_EVENT_TYPES = new Set(['llm_request', 'llm_response'])
export const SETUP_STEP_EVENT_TYPE = 'context_prepare_setup_step'
export const START_STATE_STEP_EVENT_TYPE = 'context_prepare_start_state_step'
const PREVIEW_MAX_CHARS = 1200

export function formatAttemptLabel(attemptIndex: number | null | undefined, t: Translate): string | null {
  if (attemptIndex == null || attemptIndex < 0) {
    return null
  }
  return t('runDetail.timeline.attemptLabel', { attempt: attemptIndex + 1 })
}

export function formatAttemptLabelForTitle(attemptIndex: number | null | undefined, t: Translate): string | null {
  if (attemptIndex == null || attemptIndex <= 0) {
    return null
  }
  return formatAttemptLabel(attemptIndex, t)
}

export function compactMultiline(value: string | null): string | null {
  if (!value) {
    return null
  }
  const compact = value
    .split('\n')
    .map(line => line.trim())
    .filter(Boolean)
    .join(' ')
    .replace(/\s+/g, ' ')
    .trim()
  return compact || null
}

export function truncatePreviewText(text: string | null): string | null {
  if (!text) {
    return null
  }
  if (text.length <= PREVIEW_MAX_CHARS) {
    return text
  }
  return `${text.slice(0, PREVIEW_MAX_CHARS).trimEnd()}...`
}

export function truncateLlmPreview(text: string | null): string | null {
  return truncatePreviewText(text)
}

export function asEventRecord(item: OperationEventItem): Record<string, unknown> | null {
  return asObject(item as unknown)
}

export function uniqueParts(parts: Array<string | null>): string[] {
  const seen = new Set<string>()
  const items: string[] = []

  for (const part of parts) {
    if (!part || seen.has(part)) {
      continue
    }
    seen.add(part)
    items.push(part)
  }

  return items
}

export function detailRow(label: string, value: string | null | undefined): RunTimelineDetailRow | null {
  if (!value) {
    return null
  }
  return { label, value }
}

export function formatBoolean(value: unknown): string | null {
  if (typeof value !== 'boolean') {
    return null
  }
  return value ? 'Yes' : 'No'
}

export function formatNumber(value: unknown): string | null {
  return typeof value === 'number' ? String(value) : null
}

export function formatPreExecuteStatus(value: unknown): string | null {
  if (typeof value !== 'string' || value.length === 0) {
    return null
  }
  const labels: Record<string, string> = {
    matched: 'Matched',
    passthrough: 'Passthrough',
    visual_fallback: 'Visual fallback',
    invalidated: 'Invalidated',
  }
  return labels[value] ?? prettifyToken(value)
}

export function getPreExecuteStatus(data: Record<string, unknown> | null): string | null {
  const explicitStatus = asString(data?.pre_execute_status)
  if (explicitStatus) {
    return explicitStatus
  }
  if (data?.pre_execute_invalidated === true) {
    return 'invalidated'
  }
  if (data?.pre_execute_rebound === true) {
    return 'matched'
  }
  return null
}

export function translateTimelineToken(
  t: Translate,
  group: 'roles' | 'scopes' | 'phases',
  value: string | null,
): string | null {
  if (!value) {
    return null
  }
  const key = `runDetail.timeline.${group}.${value}`
  const translated = t(key)
  return translated === key ? prettifyToken(value) : translated
}

export function withAttemptSuffix(title: string, attemptLabel: string | null): string {
  if (!attemptLabel) {
    return title
  }
  return `${title} (${attemptLabel})`
}

export function joinStringArray(value: unknown, separator = ', '): string | null {
  const items = Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0)
    : []
  return items.join(separator) || null
}

export function joinNumberArray(value: unknown, separator = ', '): string | null {
  const items = Array.isArray(value)
    ? value
      .map(item => (typeof item === 'number' ? String(item) : null))
      .filter((item): item is string => item != null)
    : []
  return items.join(separator) || null
}

export function readCanonicalStringField(
  record: Record<string, unknown> | null,
  data: Record<string, unknown> | null,
  key: string,
): string | null {
  return asString(record?.[key]) ?? asString(data?.[key])
}

export function readCanonicalNumberField(
  record: Record<string, unknown> | null,
  data: Record<string, unknown> | null,
  key: string,
): number | null {
  return asNumber(record?.[key]) ?? asNumber(data?.[key])
}
