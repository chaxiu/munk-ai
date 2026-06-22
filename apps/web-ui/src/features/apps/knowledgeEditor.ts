import type {
  KnowledgeCandidateDraft,
  KnowledgeCard,
  KnowledgeCardInput,
  KnowledgeCardStatus,
  KnowledgeCardType,
  KnowledgeSourceKind,
} from '@/shared/api/knowledge'
import { getKnowledgePayloadSections } from '@/features/apps/knowledgeFieldConfig'

export type KnowledgeEditorMode = 'structured' | 'json'
export type KnowledgePayloadDraftValue = string | string[]
export type KnowledgePayloadDraft = Record<string, KnowledgePayloadDraftValue>

export type KnowledgeCardEditorErrors = {
  title: string | null
  confidence: string | null
  payload: string | null
  payloadFields: Record<string, string>
}

export type KnowledgeCardEditorForm = {
  cardId: string
  title: string
  cardType: KnowledgeCardType
  status: KnowledgeCardStatus
  confidence: string
  sourceKind: KnowledgeSourceKind
  sourceRef: string
  sourceNote: string
  payloadDraft: KnowledgePayloadDraft
  jsonModeText: string
  editorMode: KnowledgeEditorMode
}

export function createEmptyKnowledgeCardForm(cardType: KnowledgeCardType = 'screen'): KnowledgeCardEditorForm {
  const payloadDraft = defaultPayloadByType(cardType)
  return {
    cardId: '',
    title: '',
    cardType,
    status: 'active',
    confidence: '0.8',
    sourceKind: 'manual',
    sourceRef: '',
    sourceNote: '',
    payloadDraft,
    jsonModeText: serializePayloadDraft(payloadDraft),
    editorMode: 'structured',
  }
}

export function formFromKnowledgeCard(card: KnowledgeCard): KnowledgeCardEditorForm {
  const payloadDraft = normalizePayloadByType(card.card_type, card.payload)
  return {
    cardId: card.card_id,
    title: card.title,
    cardType: card.card_type,
    status: card.status,
    confidence: String(card.confidence),
    sourceKind: card.source.kind,
    sourceRef: card.source.ref ?? '',
    sourceNote: card.source.note ?? '',
    payloadDraft,
    jsonModeText: serializePayloadDraft(payloadDraft),
    editorMode: 'structured',
  }
}

export function updateFormCardType(
  form: KnowledgeCardEditorForm,
  nextCardType: KnowledgeCardType,
): KnowledgeCardEditorForm {
  if (form.cardType === nextCardType) {
    return form
  }
  const payloadDraft = defaultPayloadByType(nextCardType)
  return {
    ...form,
    cardType: nextCardType,
    payloadDraft,
    jsonModeText: serializePayloadDraft(payloadDraft),
  }
}

export function updateFormEditorMode(
  form: KnowledgeCardEditorForm,
  nextMode: KnowledgeEditorMode,
): KnowledgeCardEditorForm {
  if (form.editorMode === nextMode) {
    return form
  }
  if (nextMode === 'json') {
    return {
      ...form,
      editorMode: 'json',
      jsonModeText: serializePayloadDraft(form.payloadDraft),
    }
  }
  const payloadDraft = parsePayloadJson(form.cardType, form.jsonModeText)
  return {
    ...form,
    editorMode: 'structured',
    payloadDraft,
    jsonModeText: serializePayloadDraft(payloadDraft),
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
  const payload = input.form.editorMode === 'json'
    ? parsePayloadJson(input.form.cardType, input.form.jsonModeText)
    : normalizePayloadByType(input.form.cardType, input.form.payloadDraft)
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

export function createEmptyKnowledgeCardEditorErrors(): KnowledgeCardEditorErrors {
  return {
    title: null,
    confidence: null,
    payload: null,
    payloadFields: {},
  }
}

export function validateKnowledgeCardForm(form: KnowledgeCardEditorForm): {
  isValid: boolean
  normalizedForm: KnowledgeCardEditorForm
  errors: KnowledgeCardEditorErrors
} {
  const errors = createEmptyKnowledgeCardEditorErrors()
  const normalizedForm: KnowledgeCardEditorForm = {
    ...form,
    title: form.title.trim(),
    sourceRef: form.sourceRef,
    sourceNote: form.sourceNote,
  }

  if (!normalizedForm.title) {
    errors.title = 'title-required'
  }

  const confidence = Number.parseFloat(form.confidence)
  if (Number.isNaN(confidence) || confidence < 0 || confidence > 1) {
    errors.confidence = 'confidence-invalid'
  }

  let payloadDraft: KnowledgePayloadDraft
  if (form.editorMode === 'json') {
    try {
      payloadDraft = parsePayloadJson(form.cardType, form.jsonModeText)
      normalizedForm.jsonModeText = serializePayloadDraft(payloadDraft)
    } catch {
      errors.payload = 'payload-invalid'
      return {
        isValid: false,
        normalizedForm,
        errors,
      }
    }
  } else {
    payloadDraft = normalizePayloadByType(form.cardType, form.payloadDraft)
  }

  normalizedForm.payloadDraft = payloadDraft

  for (const section of getKnowledgePayloadSections(form.cardType)) {
    for (const field of section.fields) {
      if (!field.required) {
        continue
      }
      const value = payloadDraft[field.key]
      const isEmpty = field.kind === 'string-list'
        ? !Array.isArray(value) || value.length === 0
        : typeof value !== 'string' || !value.trim()
      if (isEmpty) {
        errors.payloadFields[field.key] = 'field-required'
      }
    }
  }

  normalizedForm.jsonModeText = serializePayloadDraft(payloadDraft)

  return {
    isValid: !errors.title && !errors.confidence && !errors.payload && Object.keys(errors.payloadFields).length === 0,
    normalizedForm,
    errors,
  }
}

export function shouldConfirmCardTypeReset(form: KnowledgeCardEditorForm): boolean {
  const currentPayload = form.editorMode === 'json'
    ? safelyParsePayloadJson(form.cardType, form.jsonModeText) ?? normalizePayloadByType(form.cardType, form.payloadDraft)
    : normalizePayloadByType(form.cardType, form.payloadDraft)
  return serializePayloadDraft(currentPayload) !== serializePayloadDraft(defaultPayloadByType(form.cardType))
}

export function normalizePayloadByType(cardType: KnowledgeCardType, payload: unknown): KnowledgePayloadDraft {
  const base = defaultPayloadByType(cardType)
  const record = payload && typeof payload === 'object' ? payload as Record<string, unknown> : {}

  for (const section of getKnowledgePayloadSections(cardType)) {
    for (const field of section.fields) {
      if (field.kind === 'string-list') {
        base[field.key] = stringArrayValue(record[field.key])
        continue
      }
      base[field.key] = stringValue(record[field.key])
    }
  }

  return base
}

export function parsePayloadJson(cardType: KnowledgeCardType, jsonText: string): KnowledgePayloadDraft {
  let payload: unknown
  try {
    payload = JSON.parse(jsonText || '{}')
  } catch {
    throw new Error('payload must be valid JSON')
  }
  return normalizePayloadByType(cardType, payload)
}

export function serializePayloadDraft(payloadDraft: KnowledgePayloadDraft): string {
  return JSON.stringify(payloadDraft, null, 2)
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

function defaultPayloadByType(cardType: KnowledgeCardType): KnowledgePayloadDraft {
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
  return Array.isArray(value)
    ? value
        .filter((item): item is string => typeof item === 'string')
        .map(item => item.trim())
        .filter(Boolean)
    : []
}

function safelyParsePayloadJson(cardType: KnowledgeCardType, jsonText: string): KnowledgePayloadDraft | null {
  try {
    return parsePayloadJson(cardType, jsonText)
  } catch {
    return null
  }
}
