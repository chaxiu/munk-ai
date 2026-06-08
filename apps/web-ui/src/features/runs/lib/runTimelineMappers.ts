import type { OperationEventsData } from '@/shared/api/operations'
import type { Translate } from './runMapperShared'
import { asNumber, asObject, asString, asStringArray } from './runMapperShared'

export type RunTimelineEventView = {
  title: string
  description: string | null
  category: 'orchestration' | 'runtime'
  categoryLabel: string
}

const ORCHESTRATION_EVENT_TYPES = new Set([
  'workflow_started',
  'workflow_attempt_started',
  'workflow_attempt_finished',
  'workflow_retry_scheduled',
  'workflow_finished',
  'judge_decision',
])

function formatAttemptLabel(attemptIndex: number | null | undefined, t: Translate): string | null {
  if (attemptIndex == null || attemptIndex < 0) {
    return null
  }
  return t('runDetail.timeline.attemptLabel', { attempt: attemptIndex + 1 })
}

function compactMultiline(value: string | null): string | null {
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

export function presentRunTimelineEvent(
  item: NonNullable<OperationEventsData['items']>[number],
  t: Translate,
): RunTimelineEventView {
  const data = asObject(item.data_json)
  const attemptIndex = asNumber(data?.attempt_index)
  const retryAttempt = asNumber(data?.retry_attempt)
  const reason = asString(data?.reason)
  const retryReason = asString(data?.retry_reason) ?? reason
  const verdict = asString(data?.verdict)
  const decisionType = asString(data?.decision_type)
  const focusItems = asStringArray(data?.focus_items)
  const handoffSummary = compactMultiline(asString(data?.handoff_summary))
  const category: RunTimelineEventView['category'] = ORCHESTRATION_EVENT_TYPES.has(item.event_type)
    ? 'orchestration'
    : 'runtime'
  const categoryLabel = t(`runDetail.timeline.categories.${category}`)
  const attemptLabel = formatAttemptLabel(attemptIndex, t)

  if (item.event_type === 'workflow_started') {
    return {
      title: t('runDetail.timeline.events.workflowStarted'),
      description: item.message ?? null,
      category,
      categoryLabel,
    }
  }
  if (item.event_type === 'workflow_attempt_started') {
    return {
      title: attemptLabel
        ? t('runDetail.timeline.events.workflowAttemptStarted', { attempt: attemptIndex! + 1 })
        : t('runDetail.timeline.events.workflowAttemptStartedGeneric'),
      description: item.message ?? null,
      category,
      categoryLabel,
    }
  }
  if (item.event_type === 'workflow_attempt_finished') {
    const parts = [attemptLabel, verdict ? t('runDetail.timeline.verdictLabel', { verdict }) : null].filter(Boolean)
    return {
      title: attemptLabel
        ? t('runDetail.timeline.events.workflowAttemptFinished', { attempt: attemptIndex! + 1 })
        : t('runDetail.timeline.events.workflowAttemptFinishedGeneric'),
      description: parts.join(' · ') || item.message || null,
      category,
      categoryLabel,
    }
  }
  if (item.event_type === 'judge_decision') {
    const decisionKey = decisionType && ['finish', 'retry_with_context', 'escalate'].includes(decisionType)
      ? decisionType
      : 'default'
    const parts = [
      verdict ? t('runDetail.timeline.verdictLabel', { verdict }) : null,
      reason,
    ].filter(Boolean)
    return {
      title: t(`runDetail.timeline.events.judgeDecision.${decisionKey}`),
      description: parts.join(' · ') || item.message || null,
      category,
      categoryLabel,
    }
  }
  if (item.event_type === 'workflow_retry_scheduled') {
    const parts = [
      retryReason ? t('runDetail.timeline.retryReasonLabel', { reason: retryReason }) : null,
      focusItems.length > 0
        ? t('runDetail.timeline.focusItemsLabel', { focus: focusItems.join(' | ') })
        : null,
      focusItems.length === 0 && handoffSummary
        ? t('runDetail.timeline.handoffSummaryLabel', { summary: handoffSummary })
        : null,
    ].filter(Boolean)
    return {
      title: retryAttempt != null && retryAttempt > 0
        ? t('runDetail.timeline.events.workflowRetryScheduledWithAttempt', { attempt: retryAttempt })
        : t('runDetail.timeline.events.workflowRetryScheduled'),
      description: parts.join(' · ') || item.message || null,
      category,
      categoryLabel,
    }
  }
  if (item.event_type === 'workflow_finished') {
    const parts = [
      verdict ? t('runDetail.timeline.verdictLabel', { verdict }) : null,
      decisionType ? t('runDetail.timeline.decisionLabel', { decision: decisionType }) : null,
    ].filter(Boolean)
    return {
      title: t('runDetail.timeline.events.workflowFinished'),
      description: parts.join(' · ') || item.message || null,
      category,
      categoryLabel,
    }
  }
  return {
    title: item.message || item.event_type,
    description: null,
    category,
    categoryLabel,
  }
}
