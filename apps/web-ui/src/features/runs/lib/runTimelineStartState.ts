import type { Translate } from './runMapperShared'
import type { OperationEventItem, RunTimelineEventView, RunTimelineSetupSection } from './runTimelineTypes'
import { asNumber, asObject, asString } from './runMapperShared'
import {
  formatAttemptLabel,
  formatAttemptLabelForTitle,
  START_STATE_STEP_EVENT_TYPE,
  translateTimelineToken,
  truncatePreviewText,
  uniqueParts,
  withAttemptSuffix,
} from './runTimelineShared'

export { START_STATE_STEP_EVENT_TYPE }

function appendSection(
  sections: RunTimelineSetupSection[],
  id: string,
  label: string,
  fullText: string | null,
) {
  if (!fullText) {
    return
  }
  const previewText = truncatePreviewText(fullText)
  if (!previewText) {
    return
  }
  sections.push({
    id,
    label,
    previewText,
    fullText,
  })
}

function translateSkipReason(t: Translate, skipReason: string | null): string | null {
  if (!skipReason) {
    return null
  }
  const key = `runDetail.timeline.startState.skipReason.${skipReason}`
  const translated = t(key)
  return translated === key ? skipReason : translated
}

function buildStartStateSections(
  data: Record<string, unknown> | null,
  t: Translate,
): RunTimelineSetupSection[] {
  if (!data) {
    return []
  }

  const sections: RunTimelineSetupSection[] = []
  const skipReason = asString(data.skip_reason)
  if (skipReason) {
    appendSection(
      sections,
      'skip_reason',
      t('runDetail.timeline.startState.sections.skipReason'),
      translateSkipReason(t, skipReason),
    )
  }
  appendSection(
    sections,
    'error_message',
    t('runDetail.timeline.startState.sections.error'),
    asString(data.error_message),
  )
  return sections
}

function buildStartStateTitle(data: Record<string, unknown> | null, t: Translate): string {
  const outcome = asString(data?.outcome)
  const failedSuffix = outcome === 'failed' ? t('runDetail.timeline.startState.failedSuffix') : ''
  const skippedSuffix = outcome === 'skipped' ? t('runDetail.timeline.startState.skippedSuffix') : ''
  const suffix = failedSuffix || skippedSuffix
  const stepKind = asString(data?.step_kind)

  if (stepKind === 'unlock') {
    return t('runDetail.timeline.startState.titleUnlock', { suffix })
  }

  if (stepKind === 'app_reset') {
    const identity = asString(data?.entry_identity) ?? 'app'
    return t('runDetail.timeline.startState.titleAppReset', { identity, suffix })
  }

  if (stepKind === 'page_navigation') {
    const pageId = asString(data?.page_id) ?? 'page'
    return t('runDetail.timeline.startState.titlePageNavigation', { pageId, suffix })
  }

  const stepIndex = asNumber(data?.step_index)
  const indexLabel = stepIndex != null ? String(stepIndex + 1) : '?'
  return t('runDetail.timeline.startState.titleGeneric', { index: indexLabel, suffix })
}

function buildStartStateDescription(data: Record<string, unknown> | null, t: Translate): string | null {
  const parts: Array<string | null> = []
  const durationMs = asNumber(data?.duration_ms)
  if (durationMs != null) {
    parts.push(t('runDetail.timeline.startState.durationLabel', { durationMs }))
  }

  const outcome = asString(data?.outcome)
  if (outcome) {
    parts.push(t(`runDetail.timeline.startState.outcome.${outcome}`))
  }

  const skipReason = translateSkipReason(t, asString(data?.skip_reason))
  if (skipReason) {
    parts.push(skipReason)
  }

  const stepIndex = asNumber(data?.step_index)
  const stepTotal = asNumber(data?.step_total)
  if (stepIndex != null && stepTotal != null) {
    parts.push(t('runDetail.timeline.startState.stepPosition', {
      index: stepIndex + 1,
      total: stepTotal,
    }))
  }

  return uniqueParts(parts).join(' · ') || null
}

export function presentStartStateStepRunTimelineEvent(item: OperationEventItem, t: Translate): RunTimelineEventView {
  const data = asObject(item.data_json)
  const roleLabel = translateTimelineToken(t, 'roles', asString(item.agent_role) ?? asString(data?.agent_role))
  const attemptLabel = formatAttemptLabel(item.attempt_index, t)
  const outcome = asString(data?.outcome)
  const failed = outcome === 'failed'
  const skipped = outcome === 'skipped'

  return {
    kind: 'start_state_step',
    title: withAttemptSuffix(buildStartStateTitle(data, t), formatAttemptLabelForTitle(item.attempt_index, t)),
    description: buildStartStateDescription(data, t),
    category: 'runtime',
    categoryLabel: t('runDetail.timeline.categories.runtime'),
    roleLabel,
    scopeLabel: translateTimelineToken(t, 'scopes', asString(item.timeline_scope)),
    phaseLabel: translateTimelineToken(t, 'phases', asString(item.timeline_phase)),
    attemptLabel,
    eventTypeLabel: item.event_type,
    rawData: data,
    detailRows: [],
    failed,
    skipped,
    startStateSections: buildStartStateSections(data, t),
    defaultExpandedSectionIds: failed ? ['error_message'] : undefined,
  }
}
