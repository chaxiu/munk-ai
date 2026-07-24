import type { Translate } from './runMapperShared'
import type { OperationEventItem, RunTimelineEventView } from './runTimelineTypes'
import { asNumber, asObject, asString, prettifyToken } from './runMapperShared'
import { formatAttemptLabel, translateTimelineToken, truncateLlmPreview, uniqueParts } from './runTimelineShared'

function buildLlmDescriptionParts(data: Record<string, unknown> | null, t: Translate): string[] {
  const llmProvider = asString(data?.llm_provider)
  const llmModel = asString(data?.llm_model)
  const llmRequestId = asString(data?.llm_request_id)
  const llmStatusCode = asNumber(data?.llm_status_code)
  const parts: Array<string | null> = []

  if (llmProvider && llmModel) {
    parts.push(t('runDetail.timeline.llm.providerModelLabel', { provider: llmProvider, model: llmModel }))
  }
  else {
    parts.push(llmModel ?? llmProvider)
  }

  if (llmStatusCode != null) {
    parts.push(t('runDetail.timeline.llm.statusCodeLabel', { statusCode: llmStatusCode }))
  }
  if (llmRequestId) {
    parts.push(t('runDetail.timeline.llm.requestIdLabel', { requestId: llmRequestId }))
  }

  return uniqueParts(parts)
}

function buildLlmTitle(
  item: OperationEventItem,
  data: Record<string, unknown> | null,
  t: Translate,
): { title: string; roleLabel: string | null } {
  const agentRole = asString(item.agent_role) ?? asString(data?.agent_role)
  const roleLabel = translateTimelineToken(t, 'roles', agentRole)
  const key = item.event_type === 'llm_request'
    ? 'runDetail.timeline.llm.requestTitle'
    : 'runDetail.timeline.llm.responseTitle'
  return {
    title: t(key, { role: roleLabel ?? prettifyToken(agentRole ?? 'llm') }),
    roleLabel,
  }
}

export function presentLlmRunTimelineEvent(item: OperationEventItem, t: Translate): RunTimelineEventView {
  const data = asObject(item.data_json)
  const { title, roleLabel } = buildLlmTitle(item, data, t)
  const llmText = asString(data?.llm_text)
  const llmProvider = asString(data?.llm_provider)
  const llmModel = asString(data?.llm_model)
  const llmRequestId = asString(data?.llm_request_id)
  const llmStatusCode = asNumber(data?.llm_status_code)

  return {
    kind: 'llm',
    title,
    description: buildLlmDescriptionParts(data, t).join(' · ') || null,
    category: 'runtime',
    categoryLabel: t('runDetail.timeline.categories.runtime'),
    roleLabel,
    scopeLabel: null,
    phaseLabel: null,
    attemptLabel: formatAttemptLabel(item.attempt_index, t),
    eventTypeLabel: item.event_type,
    rawData: data,
    detailRows: [],
    llmPreviewText: truncateLlmPreview(llmText),
    llmFullText: llmText,
    llmRequestId,
    llmProvider,
    llmModel,
    llmStatusCode,
  }
}
