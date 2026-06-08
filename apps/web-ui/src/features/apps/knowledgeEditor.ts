import type {
  KnowledgeCandidateDraft,
  KnowledgeCard,
  KnowledgeCardInput,
  KnowledgeCardStatus,
  KnowledgeCardType,
  KnowledgeSourceKind,
} from '@/shared/api/knowledge'

export type KnowledgeCardEditorForm = {
  cardId: string
  title: string
  cardType: KnowledgeCardType
  status: KnowledgeCardStatus
  confidence: string
  sourceKind: KnowledgeSourceKind
  sourceRef: string
  sourceNote: string
  payloadText: string
}

export function createEmptyKnowledgeCardForm(cardType: KnowledgeCardType = 'screen'): KnowledgeCardEditorForm {
  return {
    cardId: '',
    title: '',
    cardType,
    status: 'active',
    confidence: '0.8',
    sourceKind: 'manual',
    sourceRef: '',
    sourceNote: '',
    payloadText: JSON.stringify(defaultPayloadByType(cardType), null, 2),
  }
}

export function formFromKnowledgeCard(card: KnowledgeCard): KnowledgeCardEditorForm {
  return {
    cardId: card.card_id,
    title: card.title,
    cardType: card.card_type,
    status: card.status,
    confidence: String(card.confidence),
    sourceKind: card.source.kind,
    sourceRef: card.source.ref ?? '',
    sourceNote: card.source.note ?? '',
    payloadText: JSON.stringify(card.payload, null, 2),
  }
}

export function updateFormCardType(
  form: KnowledgeCardEditorForm,
  nextCardType: KnowledgeCardType,
): KnowledgeCardEditorForm {
  if (form.cardType === nextCardType) {
    return form
  }
  return {
    ...form,
    cardType: nextCardType,
    payloadText: JSON.stringify(defaultPayloadByType(nextCardType), null, 2),
  }
}

export function toKnowledgeCardInput(input: {
  appId: string
  form: KnowledgeCardEditorForm
  includeCardId?: boolean
}): KnowledgeCardInput {
  const confidence = Number.parseFloat(input.form.confidence)
  if (Number.isNaN(confidence) || confidence < 0 || confidence > 1) {
    throw new Error('confidence must be between 0 and 1')
  }
  let payload: unknown
  try {
    payload = JSON.parse(input.form.payloadText || '{}')
  } catch {
    throw new Error('payload must be valid JSON')
  }
  const base = {
    app_id: input.appId,
    title: input.form.title.trim(),
    card_type: input.form.cardType,
    status: input.form.status,
    confidence,
    source: {
      kind: input.form.sourceKind,
      ref: input.form.sourceRef.trim() || null,
      note: input.form.sourceNote.trim() || null,
    },
    payload,
  }
  if (input.includeCardId && input.form.cardId.trim()) {
    return {
      ...base,
      card_id: input.form.cardId.trim(),
    } as KnowledgeCardInput
  }
  return base as KnowledgeCardInput
}

export function summarizeKnowledgeCard(card: Pick<KnowledgeCard, 'card_type' | 'payload'>): string {
  return summarizeKnowledgePayload(card.card_type, card.payload)
}

export function summarizeKnowledgeCandidate(candidate: Pick<KnowledgeCandidateDraft, 'card_type' | 'payload'>): string {
  return summarizeKnowledgePayload(candidate.card_type, candidate.payload)
}

function summarizeKnowledgePayload(cardType: KnowledgeCardType, payload: unknown): string {
  if (!payload || typeof payload !== 'object') {
    return ''
  }
  const record = payload as Record<string, unknown>
  if (cardType === 'flow') {
    return stringValue(record.goal)
  }
  if (cardType === 'assertion') {
    return stringValue(record.when)
  }
  if (cardType === 'screen') {
    return stringValue(record.recognize) || stringValue(record.enter)
  }
  if (cardType === 'issue') {
    return stringArrayValue(record.symptoms)[0] ?? stringValue(record.workaround)
  }
  if (cardType === 'data') {
    return stringArrayValue(record.fixtures)[0] ?? stringArrayValue(record.accounts)[0] ?? ''
  }
  if (cardType === 'policy') {
    return stringArrayValue(record.platform_constraints)[0] ?? stringArrayValue(record.risk_controls)[0] ?? ''
  }
  return stringValue(record.meaning) || stringValue(record.term)
}

function defaultPayloadByType(cardType: KnowledgeCardType): Record<string, unknown> {
  if (cardType === 'screen') {
    return {
      enter: '',
      recognize: '',
      key_elements: [],
      exit_signals: [],
    }
  }
  if (cardType === 'flow') {
    return {
      goal: '',
      preconditions: [],
      typical_steps: [],
      completion_signals: [],
    }
  }
  if (cardType === 'assertion') {
    return {
      when: '',
      success_signals: [],
      failure_signals: [],
      verdict_hint: '',
    }
  }
  if (cardType === 'issue') {
    return {
      symptoms: [],
      trigger_conditions: [],
      workaround: '',
      severity: '',
    }
  }
  if (cardType === 'data') {
    return {
      fixtures: [],
      accounts: [],
      preloaded_state: [],
      cleanup_requirements: [],
    }
  }
  if (cardType === 'policy') {
    return {
      platform_constraints: [],
      environment_rules: [],
      permission_rules: [],
      risk_controls: [],
    }
  }
  return {
    term: '',
    aliases: [],
    meaning: '',
    related_terms: [],
    business_scope: '',
  }
}

function stringValue(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

function stringArrayValue(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []
}
