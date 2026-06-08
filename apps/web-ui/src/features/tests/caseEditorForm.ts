import type { CaseDetailData, CaseUpsertRequest, TestCasePayload } from '@/shared/api/tests'

export type CaseEditorFormModel = {
  title: string
  intent: string
  runnerGoal: string
  preconditionsText: string
  expectedText: string
  procedureText: string
  postActionText: string
  isCoreCase: boolean
  startMode: 'reset' | 'resume'
  startPageId: string
  maxSteps: string
  maxSeconds: string
}

export function createCaseEditorForm(detail: CaseDetailData): CaseEditorFormModel {
  return {
    title: detail.title,
    intent: detail.intent,
    runnerGoal: detail.runner_goal,
    preconditionsText: formatList(detail.preconditions ?? []),
    expectedText: formatList(detail.expected ?? []),
    procedureText: formatList(detail.procedure ?? []),
    postActionText: formatList(detail.post_action ?? []),
    isCoreCase: detail.is_core_case,
    startMode: detail.start_mode === 'resume' ? 'resume' : 'reset',
    startPageId: detail.start_page_id ?? '',
    maxSteps: formatOptionalNumber(detail.max_steps),
    maxSeconds: formatOptionalNumber(detail.max_seconds),
  }
}

export function createCaseEditorFormFromPayload(payload: TestCasePayload): CaseEditorFormModel {
  const startState = payload.start_state ?? { mode: 'reset', page_id: null }
  return {
    title: payload.title,
    intent: payload.intent,
    runnerGoal: payload.runner_goal,
    preconditionsText: formatList(payload.preconditions ?? []),
    expectedText: formatList(payload.expected ?? []),
    procedureText: formatList(payload.procedure ?? []),
    postActionText: formatList(payload.post_action ?? []),
    isCoreCase: payload.is_core_case,
    startMode: startState.mode === 'resume' ? 'resume' : 'reset',
    startPageId: startState.page_id ?? '',
    maxSteps: formatOptionalNumber(payload.budget?.max_steps),
    maxSeconds: formatOptionalNumber(payload.budget?.max_seconds),
  }
}

export function buildCaseUpsertRequest(form: CaseEditorFormModel, caseId: string): CaseUpsertRequest {
  return {
    case: {
      case_id: caseId,
      title: normalizeRequiredText(form.title, 'title'),
      intent: normalizeRequiredText(form.intent, 'intent'),
      runner_goal: normalizeRequiredText(form.runnerGoal, 'runner_goal'),
      preconditions: parseListText(form.preconditionsText),
      expected: parseListText(form.expectedText),
      procedure: parseListText(form.procedureText),
      post_action: parseListText(form.postActionText),
      is_core_case: form.isCoreCase,
      budget: {
        max_steps: parseOptionalInteger(form.maxSteps, 'max_steps'),
        max_seconds: parseOptionalInteger(form.maxSeconds, 'max_seconds'),
      },
      start_state: {
        mode: form.startMode,
        page_id: normalizeOptionalText(form.startPageId),
      },
    },
  }
}

export function createCaseRequest(input: {
  title: string
  intent: string
  runnerGoal: string
  existingCaseIds: string[]
}): CaseUpsertRequest {
  return {
    case: {
      case_id: getNextCaseId(input.existingCaseIds),
      title: normalizeRequiredText(input.title, 'title'),
      intent: normalizeRequiredText(input.intent, 'intent'),
      runner_goal: normalizeRequiredText(input.runnerGoal, 'runner_goal'),
      preconditions: [],
      expected: [],
      procedure: [],
      post_action: [],
      is_core_case: false,
      budget: {
        max_steps: null,
        max_seconds: null,
      },
      start_state: {
        mode: 'reset',
        page_id: null,
      },
      source_metadata: {},
    },
  }
}

function getNextCaseId(existingCaseIds: string[]): string {
  const existing = new Set(existingCaseIds.map((item) => item.trim()).filter(Boolean))
  let index = 1
  while (existing.has(`case-${index}`)) {
    index += 1
  }
  return `case-${index}`
}

function normalizeRequiredText(value: string, fieldName: string): string {
  const cleaned = value.trim()
  if (!cleaned) {
    throw new Error(`${fieldName} must not be empty`)
  }
  return cleaned
}

function normalizeOptionalText(value: string): string | null {
  const cleaned = value.trim()
  return cleaned || null
}

function parseListText(value: string): string[] {
  return value
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean)
}

function parseOptionalInteger(value: string, fieldName: string): number | null {
  const cleaned = value.trim()
  if (!cleaned) {
    return null
  }
  if (!/^\d+$/.test(cleaned)) {
    throw new Error(`${fieldName} must be a non-negative integer`)
  }
  return Number.parseInt(cleaned, 10)
}

function formatList(items: string[]): string {
  return items.join('\n')
}

function formatOptionalNumber(value: number | null | undefined): string {
  if (typeof value !== 'number') {
    return ''
  }
  return String(value)
}
