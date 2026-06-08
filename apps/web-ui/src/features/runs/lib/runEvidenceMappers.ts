import type { OperationDetailData } from '@/shared/api/operations'
import type { Translate } from './runMapperShared'
import {
  asNumber,
  asObject,
  asString,
  prettifyToken,
} from './runMapperShared'
import { runCaseResult } from './runSummaryMappers'

type EvidencePayload = {
  path?: string
  step_index?: number
  excerpt?: unknown
}

export type RunJudgeEvidenceView = {
  evidence_id: string
  kind: string
  source: string
  summary: string
  path: string | null
  stepIndex: number | null
  excerpt: unknown | null
}

export type RunEvidenceFactView = {
  label: string
  value: string
}

export type RunEvidenceItemView = {
  evidenceId: string
  title: string
  summary: string
  badges: string[]
  facts: RunEvidenceFactView[]
  path: string | null
  rawPayload: unknown | null
  stepIndex: number | null
  sortIndex: number
}

export function judgeEvidenceItems(detail?: OperationDetailData | null): RunJudgeEvidenceView[] {
  const result = runCaseResult(detail)
  const evidence = Array.isArray(result?.evidence) ? result.evidence : []
  return evidence.map((item) => {
    const evidenceItem = asObject(item) ?? {}
    const payload = asObject(evidenceItem.payload) as EvidencePayload | null
    return {
      evidence_id: typeof evidenceItem.evidence_id === 'string' ? evidenceItem.evidence_id : '',
      kind: typeof evidenceItem.kind === 'string' ? evidenceItem.kind : '',
      source: typeof evidenceItem.source === 'string' ? evidenceItem.source : '',
      summary: typeof evidenceItem.summary === 'string' ? evidenceItem.summary : '',
      path: typeof payload?.path === 'string' ? payload.path : null,
      stepIndex: typeof payload?.step_index === 'number' ? payload.step_index : null,
      excerpt: payload?.excerpt ?? null,
    }
  }).filter((item) => Boolean(item.evidence_id))
}

function parseEmbeddedJson(text: string | null): { prefix: string | null, data: Record<string, unknown> | null } {
  if (!text) {
    return { prefix: null, data: null }
  }
  const marker = ' | data='
  const markerIndex = text.indexOf(marker)
  if (markerIndex < 0) {
    return { prefix: text, data: null }
  }
  const prefix = text.slice(0, markerIndex)
  const dataText = text.slice(markerIndex + marker.length)
  try {
    const parsed = JSON.parse(dataText)
    return { prefix, data: asObject(parsed) }
  } catch {
    return { prefix, data: null }
  }
}

function parseRunnerHistorySummary(text: string | null): { latest: string | null, outcome: string | null } {
  if (!text) {
    return { latest: null, outcome: null }
  }
  const latest = /latest=([^;]+)/.exec(text)?.[1]?.trim() ?? null
  const outcome = /outcome=(.+)$/.exec(text)?.[1]?.trim() ?? null
  return { latest, outcome }
}

function parseExecutionOutcomeSummary(text: string | null): Record<string, string> {
  if (!text) {
    return {}
  }
  return text
    .split(';')
    .map((part) => part.trim())
    .filter(Boolean)
    .reduce<Record<string, string>>((acc, part) => {
      const separatorIndex = part.indexOf('=')
      if (separatorIndex < 0) {
        return acc
      }
      const key = part.slice(0, separatorIndex).trim()
      const value = part.slice(separatorIndex + 1).trim()
      if (key && value) {
        acc[key] = value
      }
      return acc
    }, {})
}

function parseDecisionTraceSummary(text: string | null): {
  targetIdentity: string | null
  surfaceIdentity: string | null
  elementCount: string | null
} {
  if (!text) {
    return {
      targetIdentity: null,
      surfaceIdentity: null,
      elementCount: null,
    }
  }
  return {
    targetIdentity: /target_identity=([^\s]+)/.exec(text)?.[1] ?? null,
    surfaceIdentity: /surface_identity=([^\s]+)/.exec(text)?.[1] ?? null,
    elementCount: /elements=(\d+)/.exec(text)?.[1] ?? null,
  }
}

function evidenceKindLabel(kind: string | null | undefined, t: Translate): string | null {
  switch (kind) {
    case 'screen_frame':
      return t('runDetail.evidence.kinds.screenFrame')
    case 'screen_diff':
      return t('runDetail.evidence.kinds.screenDiff')
    case 'runner_history':
      return t('runDetail.evidence.kinds.runnerHistory')
    case 'execution':
      return t('runDetail.evidence.kinds.execution')
    case 'runtime_error_log':
      return t('runDetail.evidence.kinds.runtimeErrorLog')
    default:
      return prettifyToken(kind)
  }
}

function evidenceSourceLabel(source: string | null | undefined, t: Translate): string | null {
  switch (source) {
    case 'artifact':
      return t('runDetail.evidence.sources.artifact')
    case 'event':
      return t('runDetail.evidence.sources.event')
    case 'execution':
      return t('runDetail.evidence.sources.execution')
    default:
      return prettifyToken(source)
  }
}

function evidenceBadgeList(item: RunJudgeEvidenceView, t: Translate): string[] {
  const badges: string[] = []
  if (item.stepIndex != null && item.stepIndex >= 0) {
    badges.push(t('runDetail.evidence.badges.step', { step: item.stepIndex }))
  }
  const kindLabel = evidenceKindLabel(item.kind, t)
  if (kindLabel) {
    badges.push(kindLabel)
  }
  const sourceLabel = evidenceSourceLabel(item.source, t)
  if (sourceLabel) {
    badges.push(sourceLabel)
  }
  return badges
}

function buildActionProposedEvidence(
  item: RunJudgeEvidenceView,
  t: Translate,
  parsedData: Record<string, unknown> | null,
  sortIndex: number,
): RunEvidenceItemView {
  const summary = asString(parsedData?.summary) ?? item.summary
  const step = asNumber(parsedData?.step) ?? item.stepIndex
  const action = asString(parsedData?.action)
  const facts: RunEvidenceFactView[] = []
  if (step != null) {
    facts.push({ label: t('runDetail.evidence.fields.step'), value: String(step) })
  }
  if (action) {
    facts.push({ label: t('runDetail.evidence.fields.action'), value: action })
  }
  return {
    evidenceId: item.evidence_id,
    title: step != null
      ? t('runDetail.evidence.titles.actionProposedStep', { step })
      : t('runDetail.evidence.titles.actionProposed'),
    summary,
    badges: evidenceBadgeList(item, t),
    facts,
    path: item.path,
    rawPayload: parsedData ?? item.excerpt,
    stepIndex: item.stepIndex,
    sortIndex,
  }
}

function buildRunnerHistoryEvidence(item: RunJudgeEvidenceView, t: Translate, sortIndex: number): RunEvidenceItemView {
  const parsed = parseRunnerHistorySummary(item.summary)
  const summary = parsed.outcome
    ?? item.summary
    ?? t('runDetail.evidence.fallbacks.runnerHistory')
  const facts: RunEvidenceFactView[] = []
  if (parsed.latest) {
    facts.push({ label: t('runDetail.evidence.fields.latestAction'), value: parsed.latest })
  }
  if (item.stepIndex != null) {
    facts.push({ label: t('runDetail.evidence.fields.step'), value: String(item.stepIndex) })
  }
  return {
    evidenceId: item.evidence_id,
    title: t('runDetail.evidence.titles.runnerHistory'),
    summary,
    badges: evidenceBadgeList(item, t),
    facts,
    path: item.path,
    rawPayload: item.excerpt,
    stepIndex: item.stepIndex,
    sortIndex,
  }
}

function buildScreenEvidence(item: RunJudgeEvidenceView, t: Translate, sortIndex: number): RunEvidenceItemView {
  const facts: RunEvidenceFactView[] = []
  if (item.stepIndex != null) {
    facts.push({ label: t('runDetail.evidence.fields.step'), value: String(item.stepIndex) })
  }
  return {
    evidenceId: item.evidence_id,
    title: item.kind === 'screen_diff'
      ? t('runDetail.evidence.titles.screenDiff')
      : t('runDetail.evidence.titles.screenFrame'),
    summary: item.summary || t('runDetail.evidence.fallbacks.screenEvidence'),
    badges: evidenceBadgeList(item, t),
    facts,
    path: item.path,
    rawPayload: item.excerpt,
    stepIndex: item.stepIndex,
    sortIndex,
  }
}

function buildExecutionEvidence(item: RunJudgeEvidenceView, t: Translate, sortIndex: number): RunEvidenceItemView {
  const parsed = parseExecutionOutcomeSummary(item.summary)
  const facts: RunEvidenceFactView[] = []
  if (parsed.status) {
    facts.push({ label: t('runDetail.evidence.fields.status'), value: parsed.status })
  }
  if (parsed.stop_reason) {
    facts.push({ label: t('runDetail.evidence.fields.stopReason'), value: parsed.stop_reason })
  }
  if (parsed.steps_completed) {
    facts.push({ label: t('runDetail.evidence.fields.stepsCompleted'), value: parsed.steps_completed })
  }
  const summary = parsed.last_action_summary
    ?? (item.summary.startsWith('Perception completed')
      ? t('runDetail.evidence.summaries.perceptionCompleted')
      : item.summary)
    ?? t('runDetail.evidence.fallbacks.execution')
  return {
    evidenceId: item.evidence_id,
    title: t('runDetail.evidence.titles.execution'),
    summary,
    badges: evidenceBadgeList(item, t),
    facts: [
      ...(item.stepIndex != null ? [{ label: t('runDetail.evidence.fields.step'), value: String(item.stepIndex) }] : []),
      ...facts,
    ],
    path: item.path,
    rawPayload: item.excerpt,
    stepIndex: item.stepIndex,
    sortIndex,
  }
}

function buildDecisionTraceEvidence(item: RunJudgeEvidenceView, t: Translate, sortIndex: number): RunEvidenceItemView {
  const parsed = parseDecisionTraceSummary(item.summary)
  const facts: RunEvidenceFactView[] = []
  if (item.stepIndex != null) {
    facts.push({ label: t('runDetail.evidence.fields.step'), value: String(item.stepIndex) })
  }
  if (parsed.targetIdentity) {
    facts.push({ label: t('runDetail.evidence.fields.target'), value: parsed.targetIdentity })
  }
  if (parsed.surfaceIdentity) {
    facts.push({ label: t('runDetail.evidence.fields.surface'), value: parsed.surfaceIdentity })
  }
  if (parsed.elementCount) {
    facts.push({ label: t('runDetail.evidence.fields.elements'), value: parsed.elementCount })
  }
  const summary = parsed.surfaceIdentity
    ? t('runDetail.evidence.summaries.decisionTraceSurface', { surface: parsed.surfaceIdentity })
    : t('runDetail.evidence.fallbacks.decisionTrace')
  return {
    evidenceId: item.evidence_id,
    title: t('runDetail.evidence.titles.decisionTrace'),
    summary,
    badges: evidenceBadgeList(item, t),
    facts,
    path: item.path,
    rawPayload: item.excerpt,
    stepIndex: item.stepIndex,
    sortIndex,
  }
}

function buildPerceptionEvidence(item: RunJudgeEvidenceView, t: Translate, sortIndex: number): RunEvidenceItemView {
  const facts: RunEvidenceFactView[] = []
  if (item.stepIndex != null) {
    facts.push({ label: t('runDetail.evidence.fields.step'), value: String(item.stepIndex) })
  }
  return {
    evidenceId: item.evidence_id,
    title: t('runDetail.evidence.titles.perception'),
    summary: t('runDetail.evidence.summaries.perceptionCompleted'),
    badges: evidenceBadgeList(item, t),
    facts,
    path: item.path,
    rawPayload: item.excerpt,
    stepIndex: item.stepIndex,
    sortIndex,
  }
}

function buildGenericEvidence(item: RunJudgeEvidenceView, t: Translate, sortIndex: number): RunEvidenceItemView {
  const facts: RunEvidenceFactView[] = []
  if (item.stepIndex != null) {
    facts.push({ label: t('runDetail.evidence.fields.step'), value: String(item.stepIndex) })
  }
  return {
    evidenceId: item.evidence_id,
    title: evidenceKindLabel(item.kind, t) ?? t('runDetail.evidence.titles.generic'),
    summary: item.summary || t('runDetail.evidence.fallbacks.generic'),
    badges: evidenceBadgeList(item, t),
    facts,
    path: item.path,
    rawPayload: item.excerpt,
    stepIndex: item.stepIndex,
    sortIndex,
  }
}

export function presentJudgeEvidenceItem(
  item: RunJudgeEvidenceView,
  t: Translate,
  sortIndex = 0,
): RunEvidenceItemView {
  const { prefix, data } = parseEmbeddedJson(item.summary)
  const normalizedItem = {
    ...item,
    summary: prefix ?? item.summary,
  }
  if (prefix?.startsWith('action proposed for step')) {
    return buildActionProposedEvidence(normalizedItem, t, data, sortIndex)
  }
  if (item.kind === 'runner_history' || prefix?.startsWith('runner_history artifact')) {
    return buildRunnerHistoryEvidence(normalizedItem, t, sortIndex)
  }
  if (item.kind === 'decision_trace' || item.evidence_id.startsWith('trace-') || prefix?.startsWith('[SCREEN]')) {
    return buildDecisionTraceEvidence(normalizedItem, t, sortIndex)
  }
  if (prefix?.startsWith('Perception completed')) {
    return buildPerceptionEvidence(normalizedItem, t, sortIndex)
  }
  if (item.kind === 'screen_frame' || item.kind === 'screen_diff' || item.kind === 'screenshot') {
    return buildScreenEvidence(normalizedItem, t, sortIndex)
  }
  if (item.kind === 'execution' || prefix?.startsWith('execution outcome')) {
    return buildExecutionEvidence(normalizedItem, t, sortIndex)
  }
  return buildGenericEvidence(normalizedItem, t, sortIndex)
}

export function presentJudgeEvidenceItems(
  detail: OperationDetailData | null | undefined,
  t: Translate,
): RunEvidenceItemView[] {
  return judgeEvidenceItems(detail)
    .map((item, index, items) => presentJudgeEvidenceItem(item, t, items.length - index))
    .sort((left, right) => {
      const leftStep = left.stepIndex ?? -1
      const rightStep = right.stepIndex ?? -1
      if (leftStep !== rightStep) {
        return rightStep - leftStep
      }
      return right.sortIndex - left.sortIndex
    })
}
