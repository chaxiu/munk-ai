import type { OperationDetailData, OperationSummaryData } from '@/shared/api/operations'

export type BadgeTone = 'neutral' | 'success' | 'error' | 'warning'
export type Translate = (key: string, params?: Record<string, unknown>) => string

export function statusTone(status?: string | null): BadgeTone {
  if (status === 'succeeded') {
    return 'success'
  }
  if (status === 'failed' || status === 'cancelled') {
    return 'error'
  }
  if (status === 'queued' || status === 'running') {
    return 'warning'
  }
  return 'neutral'
}

export function verdictTone(verdict?: string | null): BadgeTone {
  if (verdict === 'passed') {
    return 'success'
  }
  if (verdict === 'failed') {
    return 'error'
  }
  if (verdict === 'inconclusive') {
    return 'warning'
  }
  return 'neutral'
}

export function formatVerdictLabel(
  verdict: string | null | undefined,
  t: Translate,
): string {
  if (!verdict) {
    return ''
  }
  if (verdict === 'passed' || verdict === 'failed' || verdict === 'inconclusive') {
    return t(`runs.verdict.${verdict}`)
  }
  return verdict
}

export function isTerminalStatus(status?: string | null): boolean {
  return status === 'succeeded' || status === 'failed' || status === 'cancelled'
}

export function describePhase(item: Pick<OperationSummaryData, 'phase'>): string | null {
  return item.phase?.trim() || null
}

export function rawPayload(detail?: OperationDetailData | null): string {
  if (!detail) {
    return '{}'
  }
  return JSON.stringify(detail, null, 2)
}

export function asObject(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : null
}

export function asStringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0)
    : []
}

export function asNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

export function asString(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value : null
}

export function startCase(value: string): string {
  if (!value) {
    return value
  }
  return value.charAt(0).toUpperCase() + value.slice(1)
}

export function prettifyToken(value: string | null | undefined): string | null {
  if (!value) {
    return null
  }
  const normalized = value.replace(/[_-]+/g, ' ').trim()
  if (!normalized) {
    return null
  }
  return startCase(normalized)
}
