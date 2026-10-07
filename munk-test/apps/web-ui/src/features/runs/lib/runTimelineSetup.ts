import type { Translate } from './runMapperShared'
import type { OperationEventItem, RunTimelineEventView, RunTimelineSetupSection } from './runTimelineTypes'
import { asNumber, asObject, asString } from './runMapperShared'
import {
  formatAttemptLabel,
  formatAttemptLabelForTitle,
  SETUP_STEP_EVENT_TYPE,
  translateTimelineToken,
  truncatePreviewText,
  uniqueParts,
  withAttemptSuffix,
} from './runTimelineShared'

export { SETUP_STEP_EVENT_TYPE }

function formatJsonValue(value: unknown): string | null {
  if (value === null || value === undefined) {
    return null
  }
  if (typeof value === 'string') {
    return value
  }
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

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

function buildSetupSections(
  data: Record<string, unknown> | null,
  t: Translate,
): RunTimelineSetupSection[] {
  if (!data) {
    return []
  }

  const sections: RunTimelineSetupSection[] = []
  const stepKind = asString(data.step_kind)

  if (stepKind === 'http') {
    appendSection(
      sections,
      'request_body',
      t('runDetail.timeline.setup.sections.requestBody'),
      formatJsonValue(data.request_body),
    )
    appendSection(
      sections,
      'response_body',
      t('runDetail.timeline.setup.sections.responseBody'),
      asString(data.response_body),
    )
  }

  if (stepKind === 'command') {
    appendSection(
      sections,
      'stdout_tail',
      t('runDetail.timeline.setup.sections.stdout'),
      asString(data.stdout_tail),
    )
    appendSection(
      sections,
      'stderr_tail',
      t('runDetail.timeline.setup.sections.stderr'),
      asString(data.stderr_tail),
    )
  }

  appendSection(
    sections,
    'error_message',
    t('runDetail.timeline.setup.sections.error'),
    asString(data.error_message),
  )

  return sections
}

function buildSetupTitle(data: Record<string, unknown> | null, t: Translate): string {
  const failed = asString(data?.outcome) === 'failed'
  const failedSuffix = failed ? t('runDetail.timeline.setup.failedSuffix') : ''
  const stepKind = asString(data?.step_kind)

  if (stepKind === 'http') {
    const method = asString(data?.method) ?? 'HTTP'
    const base = asString(data?.base) ?? 'base'
    const path = asString(data?.path) ?? '/'
    const status = asNumber(data?.status_code)
    const statusLabel = status != null ? String(status) : '?'
    return t('runDetail.timeline.setup.titleHttp', {
      method,
      base,
      path,
      status: statusLabel,
      failedSuffix,
    })
  }

  if (stepKind === 'command') {
    const exec = asString(data?.exec) ?? 'command'
    const args = Array.isArray(data?.args)
      ? data.args.filter((item): item is string => typeof item === 'string')
      : []
    const commandLabel = args.length > 0 ? `${exec} ${args.join(' ')}` : exec
    const exitCode = asNumber(data?.exit_code)
    const exitLabel = exitCode != null ? String(exitCode) : '?'
    return t('runDetail.timeline.setup.titleCommand', {
      command: commandLabel,
      exitCode: exitLabel,
      failedSuffix,
    })
  }

  const stepIndex = asNumber(data?.step_index)
  const indexLabel = stepIndex != null ? String(stepIndex + 1) : '?'
  return t('runDetail.timeline.setup.titleGeneric', { index: indexLabel, failedSuffix })
}

function buildSetupDescription(data: Record<string, unknown> | null, t: Translate): string | null {
  const parts: Array<string | null> = []
  const durationMs = asNumber(data?.duration_ms)
  if (durationMs != null) {
    parts.push(t('runDetail.timeline.setup.durationLabel', { durationMs }))
  }

  const outcome = asString(data?.outcome)
  if (outcome) {
    parts.push(t(`runDetail.timeline.setup.outcome.${outcome}`))
  }

  const stepIndex = asNumber(data?.step_index)
  const stepTotal = asNumber(data?.step_total)
  if (stepIndex != null && stepTotal != null) {
    parts.push(t('runDetail.timeline.setup.stepPosition', {
      index: stepIndex + 1,
      total: stepTotal,
    }))
  }

  return uniqueParts(parts).join(' · ') || null
}

export function presentSetupStepRunTimelineEvent(item: OperationEventItem, t: Translate): RunTimelineEventView {
  const data = asObject(item.data_json)
  const roleLabel = translateTimelineToken(t, 'roles', asString(item.agent_role) ?? asString(data?.agent_role))
  const attemptLabel = formatAttemptLabel(item.attempt_index, t)
  const failed = asString(data?.outcome) === 'failed'

  return {
    kind: 'setup_step',
    title: withAttemptSuffix(buildSetupTitle(data, t), formatAttemptLabelForTitle(item.attempt_index, t)),
    description: buildSetupDescription(data, t),
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
    setupSections: buildSetupSections(data, t),
    defaultExpandedSectionIds: failed ? ['error_message'] : undefined,
  }
}
