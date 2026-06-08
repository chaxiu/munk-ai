import type { OperationDetailData, OperationSummaryData } from '@/shared/api/operations'
import {
  asNumber,
  asObject,
  asString,
  asStringArray,
} from './runMapperShared'

export function displayRunTitle(item: Pick<OperationSummaryData, 'title' | 'target_label' | 'operation_id'>): string {
  return item.title?.trim() || item.target_label?.trim() || item.operation_id
}

export function displayRunSubtitle(
  item: Pick<OperationSummaryData, 'target_label' | 'app_id' | 'plan_id' | 'case_id' | 'operation_id'>,
): string {
  if (item.target_label?.trim()) {
    return item.target_label
  }
  const parts = [item.app_id, item.plan_id, item.case_id].filter(Boolean)
  return parts.join(' / ') || item.operation_id
}

export function displayRunListContext(
  item: Pick<OperationSummaryData, 'app_id' | 'operation_id'>,
): string {
  return item.app_id?.trim() || item.operation_id
}

export type RunOrchestrationAttemptView = {
  attemptIndex: number
  verdict: string | null
  summary: string | null
  judgeReason: string | null
  retryReason: string | null
  supplementalContext: string[]
  missingEvidence: string[]
  confidence: number | null
}

export type RunOrchestrationSummaryView = {
  attemptCount: number
  retried: boolean
  finalDecisionType: string | null
  finalDecisionReason: string | null
  finalDecisionSummary: string | null
  latestRetryReason: string | null
  supplementalContext: string[]
}

export type TokenUsageView = {
  inputTokens: number | null
  outputTokens: number | null
  totalTokens: number | null
  cachedInputTokens: number | null
  reasoningTokens: number | null
  requestCount: number
  provider: string | null
  model: string | null
}

export type AttemptTokenUsageView = {
  attemptIndex: number
  runnerUsage: TokenUsageView | null
  judgeUsage: TokenUsageView | null
  totalUsage: TokenUsageView | null
}

export function runCaseResult(detail?: OperationDetailData | null): Record<string, unknown> | null {
  return asObject(detail?.result ?? null)
}

export function runAttemptCount(detail?: OperationDetailData | null): number {
  const result = runCaseResult(detail)
  const explicitCount = asNumber(result?.attempt_count)
  const attempts = Array.isArray(result?.attempts) ? result.attempts : []
  return Math.max(explicitCount ?? 0, attempts.length)
}

export function runAttempts(detail?: OperationDetailData | null): RunOrchestrationAttemptView[] {
  const result = runCaseResult(detail)
  const attempts = Array.isArray(result?.attempts) ? result.attempts : []
  return attempts.map((item, index) => {
    const attempt = asObject(item) ?? {}
    return {
      attemptIndex: asNumber(attempt.attempt_index) ?? index,
      verdict: asString(attempt.verdict),
      summary: asString(attempt.summary),
      judgeReason: asString(attempt.judge_reason),
      retryReason: asString(attempt.retry_reason),
      supplementalContext: asStringArray(attempt.supplemental_context),
      missingEvidence: asStringArray(attempt.missing_evidence),
      confidence: asNumber(attempt.confidence),
    }
  })
}

export function runFinalDecision(detail?: OperationDetailData | null) {
  const decision = asObject(runCaseResult(detail)?.final_decision)
  if (!decision) {
    return null
  }
  return {
    type: asString(decision.decision_type),
    reason: asString(decision.reason),
    summary: asString(decision.summary),
  }
}

export function runOrchestrationSummary(detail?: OperationDetailData | null): RunOrchestrationSummaryView | null {
  const result = runCaseResult(detail)
  if (!result) {
    return null
  }
  const attemptCount = runAttemptCount(detail)
  const attempts = runAttempts(detail)
  const finalDecision = runFinalDecision(detail)
  const latestAttempt = attempts.length > 0 ? attempts[attempts.length - 1] : null
  const supplementalContext = asStringArray(result.supplemental_context)
  return {
    attemptCount,
    retried: attemptCount > 1,
    finalDecisionType: finalDecision?.type ?? null,
    finalDecisionReason: finalDecision?.reason ?? null,
    finalDecisionSummary: finalDecision?.summary ?? null,
    latestRetryReason: latestAttempt?.retryReason ?? null,
    supplementalContext: supplementalContext.length > 0
      ? supplementalContext
      : (latestAttempt?.supplementalContext ?? []),
  }
}

export function planRunProgress(detail?: Pick<OperationDetailData, 'run_type' | 'progress'> | null) {
  if (!detail || detail.run_type !== 'plan_run') {
    return null
  }
  const progress = detail.progress ?? {}
  const totalCases = asNumber(progress.total_cases) ?? 0
  const completedCases = asNumber(progress.completed_cases) ?? 0
  const currentCaseId = asString(progress.current_case_id)
  const lastCaseId = asString(progress.last_case_id)
  const percent = totalCases > 0 ? Math.min(100, Math.max(0, Math.round((completedCases / totalCases) * 100))) : null
  return {
    totalCases,
    completedCases,
    currentCaseId,
    lastCaseId,
    percent,
  }
}

export function tokenUsageView(value: unknown): TokenUsageView | null {
  const usage = asObject(value)
  if (!usage) {
    return null
  }
  const requestCount = asNumber(usage.request_count) ?? 0
  const view = {
    inputTokens: asNumber(usage.input_tokens),
    outputTokens: asNumber(usage.output_tokens),
    totalTokens: asNumber(usage.total_tokens),
    cachedInputTokens: asNumber(usage.cached_input_tokens),
    reasoningTokens: asNumber(usage.reasoning_tokens),
    requestCount,
    provider: asString(usage.provider),
    model: asString(usage.model),
  }
  const hasValues = Object.values(view).some((item) => item != null && item !== 0 && item !== '')
  return hasValues || requestCount > 0 ? view : null
}

export function attemptTokenUsages(detail?: OperationDetailData | null): AttemptTokenUsageView[] {
  const rawAttempts = detail?.attempt_usages
  if (!Array.isArray(rawAttempts)) {
    return []
  }
  return rawAttempts.flatMap((item, index) => {
    const attempt = asObject(item)
    if (!attempt) {
      return []
    }
    return [{
      attemptIndex: asNumber(attempt.attempt_index) ?? index,
      runnerUsage: tokenUsageView(attempt.runner_usage),
      judgeUsage: tokenUsageView(attempt.judge_usage),
      totalUsage: tokenUsageView(attempt.total_usage),
    }]
  })
}

export function sceneTokenUsages(detail?: OperationDetailData | null) {
  return {
    total: tokenUsageView(detail?.token_usage),
    planning: tokenUsageView(detail?.planning_usage),
    execution: tokenUsageView(detail?.execution_usage),
    attempts: attemptTokenUsages(detail),
  }
}
