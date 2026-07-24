import type { Translate } from './runMapperShared'
import type { OperationEventItem, RunTimelineEventView } from './runTimelineTypes'
import {
  asNumber,
  asString,
  asStringArray,
} from './runMapperShared'
import {
  HISTORICAL_TIMELINE_EVENT_TYPES,
  compactMultiline,
  formatAttemptLabel,
} from './runTimelineShared'

type HistoricalContext = {
  item: OperationEventItem
  data: Record<string, unknown> | null
  t: Translate
  attemptIndex: number | null
  retryAttempt: number | null
  reason: string | null
  retryReason: string | null
  verdict: string | null
  decisionType: string | null
  focusItems: string[]
  handoffSummary: string | null
  category: RunTimelineEventView['category']
  categoryLabel: string
  attemptLabel: string | null
}

type HistoricalHandler = (context: HistoricalContext) => RunTimelineEventView

function buildHistoricalView(
  context: HistoricalContext,
  title: string,
  description: string | null,
  attemptLabel: string | null,
): RunTimelineEventView {
  return {
    kind: 'default',
    title,
    description,
    category: context.category,
    categoryLabel: context.categoryLabel,
    roleLabel: null,
    scopeLabel: null,
    phaseLabel: null,
    attemptLabel,
    eventTypeLabel: context.item.event_type,
    rawData: context.data,
    detailRows: [],
  }
}

function workflowStartedView(context: HistoricalContext): RunTimelineEventView {
  return buildHistoricalView(
    context,
    context.t('runDetail.timeline.events.workflowStarted'),
    context.item.message ?? null,
    null,
  )
}

function workflowAttemptStartedView(context: HistoricalContext): RunTimelineEventView {
  const title = context.attemptLabel
    ? context.t('runDetail.timeline.events.workflowAttemptStarted', { attempt: context.attemptIndex! + 1 })
    : context.t('runDetail.timeline.events.workflowAttemptStartedGeneric')
  return buildHistoricalView(context, title, context.item.message ?? null, context.attemptLabel)
}

function workflowAttemptFinishedView(context: HistoricalContext): RunTimelineEventView {
  const title = context.attemptLabel
    ? context.t('runDetail.timeline.events.workflowAttemptFinished', { attempt: context.attemptIndex! + 1 })
    : context.t('runDetail.timeline.events.workflowAttemptFinishedGeneric')
  const description = [
    context.attemptLabel,
    context.verdict ? context.t('runDetail.timeline.verdictLabel', { verdict: context.verdict }) : null,
  ].filter(Boolean).join(' · ') || context.item.message || null
  return buildHistoricalView(context, title, description, context.attemptLabel)
}

function judgeDecisionView(context: HistoricalContext): RunTimelineEventView {
  const supportedDecisionTypes = new Set(['finish', 'retry_with_context', 'escalate'])
  const decisionKey = context.decisionType && supportedDecisionTypes.has(context.decisionType)
    ? context.decisionType
    : 'default'
  const description = [
    context.verdict ? context.t('runDetail.timeline.verdictLabel', { verdict: context.verdict }) : null,
    context.reason,
  ].filter(Boolean).join(' · ') || context.item.message || null
  return buildHistoricalView(
    context,
    context.t(`runDetail.timeline.events.judgeDecision.${decisionKey}`),
    description,
    context.attemptLabel,
  )
}

function workflowRetryScheduledView(context: HistoricalContext): RunTimelineEventView {
  const description = [
    context.retryReason ? context.t('runDetail.timeline.retryReasonLabel', { reason: context.retryReason }) : null,
    context.focusItems.length > 0
      ? context.t('runDetail.timeline.focusItemsLabel', { focus: context.focusItems.join(' | ') })
      : null,
    context.focusItems.length === 0 && context.handoffSummary
      ? context.t('runDetail.timeline.handoffSummaryLabel', { summary: context.handoffSummary })
      : null,
  ].filter(Boolean).join(' · ') || context.item.message || null
  const title = context.retryAttempt != null && context.retryAttempt > 0
    ? context.t('runDetail.timeline.events.workflowRetryScheduledWithAttempt', { attempt: context.retryAttempt })
    : context.t('runDetail.timeline.events.workflowRetryScheduled')
  return buildHistoricalView(context, title, description, context.attemptLabel)
}

function workflowFinishedView(context: HistoricalContext): RunTimelineEventView {
  const description = [
    context.verdict ? context.t('runDetail.timeline.verdictLabel', { verdict: context.verdict }) : null,
    context.decisionType ? context.t('runDetail.timeline.decisionLabel', { decision: context.decisionType }) : null,
  ].filter(Boolean).join(' · ') || context.item.message || null
  return buildHistoricalView(
    context,
    context.t('runDetail.timeline.events.workflowFinished'),
    description,
    null,
  )
}

function defaultHistoricalView(context: HistoricalContext): RunTimelineEventView {
  return buildHistoricalView(
    context,
    context.item.message || context.item.event_type,
    null,
    context.attemptLabel,
  )
}

const HISTORICAL_HANDLERS: Record<string, HistoricalHandler> = {
  workflow_started: workflowStartedView,
  workflow_attempt_started: workflowAttemptStartedView,
  workflow_attempt_finished: workflowAttemptFinishedView,
  judge_decision: judgeDecisionView,
  workflow_retry_scheduled: workflowRetryScheduledView,
  workflow_finished: workflowFinishedView,
}

function buildHistoricalContext(
  item: OperationEventItem,
  data: Record<string, unknown> | null,
  t: Translate,
): HistoricalContext {
  const attemptIndex = asNumber(data?.attempt_index)
  const category: RunTimelineEventView['category'] = HISTORICAL_TIMELINE_EVENT_TYPES.has(item.event_type)
    ? 'orchestration'
    : 'runtime'
  return {
    item,
    data,
    t,
    attemptIndex,
    retryAttempt: asNumber(data?.retry_attempt),
    reason: asString(data?.reason),
    retryReason: asString(data?.retry_reason) ?? asString(data?.reason),
    verdict: asString(data?.verdict),
    decisionType: asString(data?.decision_type),
    focusItems: asStringArray(data?.focus_items),
    handoffSummary: compactMultiline(asString(data?.handoff_summary)),
    category,
    categoryLabel: t(`runDetail.timeline.categories.${category}`),
    attemptLabel: formatAttemptLabel(attemptIndex, t),
  }
}

export function presentHistoricalRunTimelineEvent(
  item: OperationEventItem,
  data: Record<string, unknown> | null,
  t: Translate,
): RunTimelineEventView {
  const context = buildHistoricalContext(item, data, t)
  const handler = HISTORICAL_HANDLERS[item.event_type]
  return handler ? handler(context) : defaultHistoricalView(context)
}
