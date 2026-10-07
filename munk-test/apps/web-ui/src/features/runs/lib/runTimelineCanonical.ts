import type { Translate } from './runMapperShared'
import type { OperationEventItem, RunTimelineDetailRow, RunTimelineEventView } from './runTimelineTypes'
import { asObject, asString } from './runMapperShared'
import {
  asEventRecord,
  compactMultiline,
  detailRow,
  formatAttemptLabel,
  formatAttemptLabelForTitle,
  formatBoolean,
  formatNumber,
  formatPreExecuteStatus,
  getPreExecuteStatus,
  joinNumberArray,
  joinStringArray,
  readCanonicalNumberField,
  readCanonicalStringField,
  translateTimelineToken,
  uniqueParts,
  withAttemptSuffix,
} from './runTimelineShared'

type DetailField = {
  label: string
  value: (data: Record<string, unknown> | null) => string | null
}

type DetailGroup = {
  eventTypes: Set<string>
  buildRows: (data: Record<string, unknown> | null, t: Translate) => RunTimelineDetailRow[]
}

type CanonicalOverride = {
  title?: string
  description?: string | null
  failed?: boolean
}

type TitleOverrideResolver = (
  data: Record<string, unknown> | null,
  t: Translate,
) => string | null

type CanonicalContext = {
  data: Record<string, unknown> | null
  agentRole: string | null
  timelineScope: string | null
  timelinePhase: string | null
  attemptIndex: number | null
  eventSummary: string | null
  parentOperationId: string | null
  childOperationId: string | null
  category: RunTimelineEventView['category']
  categoryLabel: string
  attemptLabel: string | null
  attemptTitleLabel: string | null
  roleLabel: string | null
  scopeLabel: string | null
  phaseLabel: string | null
}

const CANONICAL_PRESENCE_KEYS = [
  'agent_role',
  'timeline_scope',
  'timeline_phase',
  'summary',
  'parent_operation_id',
  'child_operation_id',
]

const BASE_DETAIL_FIELDS: DetailField[] = [
  { label: 'Child kind', value: data => asString(data?.child_kind) },
  { label: 'Request path', value: data => asString(data?.request_path) },
  { label: 'Trigger source', value: data => asString(data?.trigger_source) },
  { label: 'Trigger signals', value: data => joinStringArray(data?.trigger_signals) },
  { label: 'Optimization fields', value: data => joinStringArray(data?.optimization_fields) },
  { label: 'Judge result', value: data => asString(data?.judge_result_path) },
  { label: 'Error', value: data => asString(data?.error) },
  { label: 'PID', value: data => formatNumber(data?.pid) },
  { label: 'Mode', value: data => asString(data?.mode) },
  { label: 'Command', value: data => asString(data?.command) },
  { label: 'Device', value: data => asString(data?.device_ref) },
  { label: 'Reason', value: data => asString(data?.reason) },
  { label: 'Requested device', value: data => asString(data?.requested_device_ref) },
  { label: 'Blocking device', value: data => asString(data?.blocking_device_ref) },
]

const DETAIL_GROUPS: DetailGroup[] = [
  createFieldGroup(['batch_started'], [
    { label: 'Total children', value: data => formatNumber(data?.total_children) },
    { label: 'Plan IDs', value: data => joinStringArray(data?.plan_ids) },
  ]),
  createFieldGroup(['batch_child_started', 'batch_child_finished'], [
    { label: 'Title', value: data => asString(data?.title) },
    { label: 'Case ID', value: data => asString(data?.case_id) },
    { label: 'Plan ID', value: data => asString(data?.plan_id) },
    { label: 'Status', value: data => asString(data?.status) },
    { label: 'Verdict', value: data => asString(data?.verification_verdict) },
    { label: 'Position', value: data => asString(data?.position_label) },
    { label: 'Error code', value: data => asString(data?.error_code) },
    { label: 'Error message', value: data => asString(data?.error_message) },
  ]),
  createFieldGroup(['batch_stopped_early', 'batch_finished'], [
    { label: 'Plan ID', value: data => asString(data?.plan_id) },
    { label: 'Operation ID', value: data => asString(data?.operation_id) },
    { label: 'Completed children', value: data => formatNumber(data?.completed_children) },
    { label: 'Total children', value: data => formatNumber(data?.total_children) },
    { label: 'Verdict', value: data => asString(data?.verification_verdict) },
    { label: 'Stopped early', value: data => formatBoolean(data?.stopped_early) },
  ]),
  createFieldGroup(['plan_saved', 'change_plan_saved', 'change_verification_plan_saved'], [
    { label: 'App ID', value: data => asString(data?.app_id) },
    { label: 'Plan ID', value: data => asString(data?.plan_id) },
    { label: 'Case count', value: data => formatNumber(data?.case_count) },
    { label: 'Plan path', value: data => asString(data?.plan_path) },
    { label: 'Snapshot path', value: data => asString(data?.snapshot_path) },
  ]),
  createFieldGroup([
    'plan_context_loaded',
    'change_plan_context_loaded',
    'plan_agent_ready',
    'plan_case_generated',
    'plan_skeleton_outline_warning',
    'plan_skeleton_ac_coverage_warning',
    'change_verification_review_contract_loaded',
    'change_verification_cases_ready',
    'review_context_loaded',
    'review_retrieval_completed',
    'review_agent_completed',
  ], [
    { label: 'App ID', value: data => asString(data?.app_id) },
    { label: 'Case ID', value: data => asString(data?.case_id) },
    { label: 'Case title', value: data => asString(data?.case_title) },
    { label: 'Case index', value: data => formatNumber(data?.case_index) },
    { label: 'Completed cases', value: data => formatNumber(data?.completed_case_count) },
    { label: 'Target cases', value: data => formatNumber(data?.target_case_count) },
    { label: 'Has requirement doc', value: data => formatBoolean(data?.has_requirement_doc) },
    { label: 'Has technical doc', value: data => formatBoolean(data?.has_technical_doc) },
    { label: 'Has review contract', value: data => formatBoolean(data?.has_review_contract) },
    { label: 'Assets root', value: data => asString(data?.assets_root) },
    { label: 'Duplicate titles', value: data => joinStringArray(data?.duplicate_titles) },
    { label: 'Uncovered AC', value: data => joinNumberArray(data?.uncovered_indices) },
    { label: 'Review required', value: data => formatNumber(data?.review_required_case_count) },
    { label: 'Manual cases', value: data => formatNumber(data?.manual_case_count) },
    { label: 'Planner cases', value: data => formatNumber(data?.planner_case_count) },
    { label: 'Review hints', value: data => formatBoolean(data?.review_hint_enabled) },
    { label: 'Root dir', value: data => asString(data?.root_dir) },
    { label: 'Retrieval hits', value: data => formatNumber(data?.retrieval_hit_count) },
    { label: 'Prompt hits', value: data => formatNumber(data?.prompt_hit_count) },
    { label: 'Findings', value: data => formatNumber(data?.finding_count) },
    { label: 'Suggested cases', value: data => formatNumber(data?.suggested_case_count) },
  ]),
  createFieldGroup([
    'knowledge_started',
    'knowledge_agent_input_ready',
    'knowledge_evidence_ready',
    'knowledge_prompt_ready',
    'knowledge_tool_called',
    'knowledge_tool_calls_completed',
    'knowledge_result_generated',
    'knowledge_candidate_generation_completed',
    'knowledge_runtime_completed',
    'knowledge_candidate_submission_completed',
    'knowledge_result_ready',
    'knowledge_completed',
    'knowledge_skipped',
    'optimize_started',
    'optimize_request_built',
    'optimize_evidence_ready',
    'optimize_tool_called',
    'optimize_tool_calls_completed',
    'optimize_result_generated',
    'optimize_result_ready',
    'optimize_runtime_completed',
    'optimize_applied',
    'optimize_completed',
    'optimize_skipped',
    'optimize_failed',
  ], [
    { label: 'Agent input path', value: data => asString(data?.agent_input_path) },
    { label: 'Prompt path', value: data => asString(data?.prompt_path) },
    { label: 'Tool', value: data => asString(data?.tool_name) },
    { label: 'Tool index', value: data => formatNumber(data?.tool_index) },
    { label: 'Tool calls', value: data => formatNumber(data?.tool_call_count) },
    { label: 'Tool call list', value: data => joinStringArray(data?.tool_calls) },
    { label: 'Artifact count', value: data => formatNumber(data?.artifact_count) },
    { label: 'Generated candidates', value: data => formatNumber(data?.generated_candidate_count) },
    { label: 'Candidate ID', value: data => asString(data?.candidate_id) },
    { label: 'Candidate count', value: data => formatNumber(data?.candidate_count) },
    { label: 'Candidate title', value: data => asString(data?.candidate_title) },
    { label: 'Card type', value: data => asString(data?.card_type) },
    { label: 'Judge verdict', value: data => asString(data?.judge_verdict) },
    { label: 'Submitted', value: data => formatBoolean(data?.submitted) },
    { label: 'Skip reason', value: data => asString(data?.skip_reason) },
    { label: 'Attempt count', value: data => formatNumber(data?.attempt_count) },
    { label: 'Step summaries', value: data => formatNumber(data?.step_summary_count) },
    { label: 'Step screens', value: data => formatNumber(data?.step_screen_count) },
    { label: 'Step transitions', value: data => formatNumber(data?.step_transition_count) },
    { label: 'Patched fields', value: data => joinStringArray(data?.patched_fields) },
    { label: 'Patch summary', value: data => joinStringArray(data?.patched_field_summaries, ' | ') },
    { label: 'Patched count', value: data => formatNumber(data?.patched_field_count) },
    { label: 'Skipped count', value: data => formatNumber(data?.skipped_field_count) },
    { label: 'Applied', value: data => formatBoolean(data?.applied) },
    { label: 'Error type', value: data => asString(data?.error_type) },
  ]),
  {
    eventTypes: new Set(['action_proposed']),
    buildRows: (data, _t) => buildActionRows(data, false),
  },
  {
    eventTypes: new Set(['action_execution_started']),
    buildRows: (data, _t) => buildActionRows(data, true),
  },
  createContextPrepareDetailGroup(
    ['context_prepare_params_resolved'],
    (t) => [
      { label: t('runDetail.timeline.contextPrepare.details.deviceRef'), value: data => asString(data?.device_ref) },
      { label: t('runDetail.timeline.contextPrepare.details.maxSteps'), value: data => formatNumber(data?.max_steps) },
      { label: t('runDetail.timeline.contextPrepare.details.maxSeconds'), value: data => formatNumber(data?.max_seconds) },
      { label: t('runDetail.timeline.contextPrepare.details.interval'), value: data => formatNumber(data?.interval) },
      { label: t('runDetail.timeline.contextPrepare.details.initialReadyTimeoutSec'), value: data => formatNumber(data?.initial_ready_timeout_sec) },
      { label: t('runDetail.timeline.contextPrepare.details.maxSide'), value: data => formatNumber(data?.max_side) },
      { label: t('runDetail.timeline.contextPrepare.details.settleTimeout'), value: data => formatNumber(data?.settle_timeout) },
      { label: t('runDetail.timeline.contextPrepare.details.settleMode'), value: data => asString(data?.settle_mode) },
      { label: t('runDetail.timeline.contextPrepare.details.settleOcrOnly'), value: data => formatBoolean(data?.settle_ocr_only) },
      { label: t('runDetail.timeline.contextPrepare.details.settleRatioThreshold'), value: data => formatNumber(data?.settle_ratio_threshold) },
      { label: t('runDetail.timeline.contextPrepare.details.settleDelaySec'), value: data => formatNumber(data?.settle_delay_sec) },
    ],
  ),
  createContextPrepareDetailGroup(
    ['context_prepare_device_ready'],
    (t) => [
      { label: t('runDetail.timeline.contextPrepare.details.deviceRef'), value: data => asString(data?.device_ref) },
      { label: t('runDetail.timeline.contextPrepare.details.platform'), value: data => asString(data?.platform) },
    ],
  ),
  createContextPrepareDetailGroup(
    ['context_prepare_perception_ready'],
    (t) => [
      { label: t('runDetail.timeline.contextPrepare.details.maxSide'), value: data => formatNumber(data?.max_side) },
      { label: t('runDetail.timeline.contextPrepare.details.iconConf'), value: data => formatNumber(data?.icon_conf) },
    ],
  ),
  createContextPrepareDetailGroup(
    ['context_prepare_setup_ready', 'context_prepare_start_state_ready'],
    (t) => [
      { label: t('runDetail.timeline.contextPrepare.details.stepCount'), value: data => formatNumber(data?.step_count) },
      { label: t('runDetail.timeline.contextPrepare.details.durationMs'), value: data => formatNumber(data?.duration_ms) },
    ],
  ),
  createContextPrepareDetailGroup(
    ['context_prepare_failed'],
    (t) => [
      { label: t('runDetail.timeline.contextPrepare.details.failedPhase'), value: data => translateContextPrepareFailedPhase(data?.failed_phase, t) },
      { label: t('runDetail.timeline.contextPrepare.details.errorType'), value: data => asString(data?.error_type) },
      { label: t('runDetail.timeline.contextPrepare.details.errorMessage'), value: data => asString(data?.error_message) },
      { label: t('runDetail.timeline.contextPrepare.details.stepIndex'), value: data => formatNumber(data?.step_index) },
    ],
  ),
]

const TITLE_OVERRIDE_RESOLVERS: Record<string, TitleOverrideResolver> = {
  batch_started: () => 'Batch Started',
  batch_child_started: data => asString(data?.case_id) ? 'Case Started' : 'Plan Started',
  batch_child_finished: data => asString(data?.case_id) ? 'Case Finished' : 'Plan Finished',
  batch_stopped_early: () => 'Batch Stopped Early',
  batch_finished: () => 'Batch Finished',
  plan_saved: () => 'Plan Saved',
  change_plan_saved: () => 'Change Plan Saved',
  change_verification_plan_saved: () => 'Verification Plan Saved',
  review_context_loaded: () => 'Review Context Loaded',
  review_retrieval_completed: () => 'Review Retrieval Completed',
  review_agent_completed: () => 'Review Agent Completed',
  knowledge_started: () => 'Knowledge Started',
  knowledge_agent_input_ready: () => 'Knowledge Input Ready',
  knowledge_evidence_ready: () => 'Knowledge Evidence Ready',
  knowledge_prompt_ready: () => 'Knowledge Prompt Ready',
  knowledge_tool_called: () => 'Knowledge Tool Called',
  knowledge_tool_calls_completed: () => 'Knowledge Tool Calls Completed',
  knowledge_result_generated: () => 'Knowledge Result Generated',
  knowledge_candidate_generation_completed: () => 'Knowledge Candidate Generation Completed',
  knowledge_runtime_completed: () => 'Knowledge Runtime Completed',
  knowledge_candidate_submission_completed: () => 'Knowledge Candidate Submitted',
  knowledge_result_ready: () => 'Knowledge Result Ready',
  knowledge_completed: () => 'Knowledge Completed',
  knowledge_skipped: () => 'Knowledge Skipped',
  optimize_started: () => 'Optimize Started',
  optimize_request_built: () => 'Optimize Request Built',
  optimize_evidence_ready: () => 'Optimize Evidence Ready',
  optimize_tool_called: () => 'Optimize Tool Called',
  optimize_tool_calls_completed: () => 'Optimize Tool Calls Completed',
  optimize_result_generated: () => 'Optimize Result Generated',
  optimize_result_ready: () => 'Optimize Result Ready',
  optimize_runtime_completed: () => 'Optimize Runtime Completed',
  optimize_applied: () => 'Optimize Applied',
  optimize_completed: () => 'Optimize Completed',
  optimize_skipped: () => 'Optimize Skipped',
  optimize_failed: () => 'Optimize Failed',
  context_prepare_started: (_data, t) => t('runDetail.timeline.contextPrepare.started'),
  context_prepare_completed: (_data, t) => t('runDetail.timeline.contextPrepare.completed'),
  context_prepare_failed: (_data, t) => t('runDetail.timeline.contextPrepare.failed'),
  context_prepare_params_resolved: (_data, t) => t('runDetail.timeline.contextPrepare.paramsResolved'),
  context_prepare_device_ready: (_data, t) => t('runDetail.timeline.contextPrepare.deviceReady'),
  context_prepare_perception_ready: (_data, t) => t('runDetail.timeline.contextPrepare.perceptionReady'),
  context_prepare_setup_started: (_data, t) => t('runDetail.timeline.setup.started'),
  context_prepare_setup_ready: (_data, t) => t('runDetail.timeline.setup.ready'),
  context_prepare_start_state_started: (_data, t) => t('runDetail.timeline.startState.started'),
  context_prepare_start_state_ready: (_data, t) => t('runDetail.timeline.startState.ready'),
}

function createContextPrepareDetailGroup(
  eventTypes: string[],
  buildFields: (t: Translate) => DetailField[],
): DetailGroup {
  return {
    eventTypes: new Set(eventTypes),
    buildRows: (data, t) => buildDetailRows(buildFields(t), data),
  }
}

function translateContextPrepareFailedPhase(
  value: unknown,
  t: Translate,
): string | null {
  const phase = asString(value)
  if (!phase) {
    return null
  }
  const key = `runDetail.timeline.contextPrepare.failedPhase.${phase}`
  const translated = t(key)
  return translated === key ? phase : translated
}

function createFieldGroup(eventTypes: string[], fields: DetailField[]): DetailGroup {
  return {
    eventTypes: new Set(eventTypes),
    buildRows: (data, _t) => buildDetailRows(fields, data),
  }
}

function buildDetailRows(fields: DetailField[], data: Record<string, unknown> | null): RunTimelineDetailRow[] {
  return fields
    .map(field => detailRow(field.label, field.value(data)))
    .filter((row): row is RunTimelineDetailRow => row != null)
}

function buildActionRows(data: Record<string, unknown> | null, includeRebound: boolean): RunTimelineDetailRow[] {
  const rows = buildDetailRows([
    { label: 'Pre-execute status', value: value => formatPreExecuteStatus(getPreExecuteStatus(value)) },
    { label: 'Stale reason', value: value => asString(value?.stale_reason) },
    { label: 'Target match strategy', value: value => asString(value?.target_match_strategy) },
    { label: 'Target stable key', value: value => asString(value?.target_stable_key) },
  ], data)

  if (includeRebound && data?.pre_execute_rebound === true) {
    rows.splice(1, 0, { label: 'Pre-execute rebound', value: 'Yes' })
  }

  return rows
}

function resolveOverrideTitle(
  eventType: string,
  data: Record<string, unknown> | null,
  t: Translate,
): string | null {
  const override = TITLE_OVERRIDE_RESOLVERS[eventType]
  if (!override) {
    return null
  }
  return override(data, t)
}

function buildContextPrepareFailedDescription(
  data: Record<string, unknown> | null,
  t: Translate,
): string | null {
  return uniqueParts([
    translateContextPrepareFailedPhase(data?.failed_phase, t),
    asString(data?.error_message),
  ]).join(' · ') || null
}

function buildPreExecuteDescription(item: OperationEventItem, data: Record<string, unknown> | null): string | null {
  const preExecuteStatus = getPreExecuteStatus(data)

  if (item.event_type === 'action_proposed' && preExecuteStatus === 'invalidated') {
    return uniqueParts([
      'Proposal invalidated before execution.',
      asString(data?.stale_reason),
    ]).join(' · ') || null
  }

  if (item.event_type !== 'action_execution_started') {
    return null
  }

  if (preExecuteStatus === 'matched') {
    return uniqueParts([
      data?.pre_execute_rebound === true
        ? 'Target rebound on fresh screen before execution.'
        : 'Target matched on fresh screen before execution.',
      asString(data?.target_match_strategy),
    ]).join(' · ') || null
  }

  if (preExecuteStatus === 'visual_fallback') {
    return uniqueParts([
      'Target recovered by visual fallback before execution.',
      asString(data?.target_match_strategy),
    ]).join(' · ') || null
  }

  if (preExecuteStatus === 'passthrough') {
    return 'Target passed through without structured pre-execute match.'
  }

  return null
}

function buildStructuredCanonicalDetails(
  item: OperationEventItem,
  data: Record<string, unknown> | null,
  t: Translate,
): RunTimelineDetailRow[] {
  const rows = [...buildDetailRows(BASE_DETAIL_FIELDS, data)]

  for (const group of DETAIL_GROUPS) {
    if (!group.eventTypes.has(item.event_type)) {
      continue
    }
    rows.push(...group.buildRows(data, t))
  }

  return rows
}

function buildStructuredCanonicalOverrides(
  item: OperationEventItem,
  data: Record<string, unknown> | null,
  attemptTitleLabel: string | null,
  t: Translate,
): CanonicalOverride {
  if (item.event_type === 'context_prepare_failed') {
    return {
      title: withAttemptSuffix(
        resolveOverrideTitle(item.event_type, data, t) ?? t('runDetail.timeline.contextPrepare.failed'),
        attemptTitleLabel,
      ),
      description: buildContextPrepareFailedDescription(data, t),
      failed: true,
    }
  }

  const title = resolveOverrideTitle(item.event_type, data, t)
  if (!title) {
    const description = buildPreExecuteDescription(item, data)
    return description ? { description } : {}
  }

  const descriptionParts = uniqueParts([
    item.message ?? null,
    asString(data?.title),
    asString(data?.status),
    asString(data?.verification_verdict),
  ])

  return {
    title: withAttemptSuffix(title, attemptTitleLabel),
    description: descriptionParts.join(' · ') || null,
  }
}

function buildCanonicalContext(item: OperationEventItem, t: Translate): CanonicalContext {
  const record = asEventRecord(item)
  const data = asObject(item.data_json)
  const agentRole = readCanonicalStringField(record, data, 'agent_role')
  const timelineScope = readCanonicalStringField(record, data, 'timeline_scope')
  const timelinePhase = readCanonicalStringField(record, data, 'timeline_phase')
  const attemptIndex = readCanonicalNumberField(record, data, 'attempt_index')
  const summaryField = readCanonicalStringField(record, data, 'summary')
  const eventSummary = compactMultiline(summaryField ?? compactMultiline(item.message ?? null))
  const parentOperationId = readCanonicalStringField(record, data, 'parent_operation_id')
  const childOperationId = readCanonicalStringField(record, data, 'child_operation_id')
  const category: RunTimelineEventView['category'] = agentRole === 'orchestration'
    ? 'orchestration'
    : 'runtime'

  return {
    data,
    agentRole,
    timelineScope,
    timelinePhase,
    attemptIndex,
    eventSummary,
    parentOperationId,
    childOperationId,
    category,
    categoryLabel: t(`runDetail.timeline.categories.${category}`),
    attemptLabel: formatAttemptLabel(attemptIndex, t),
    attemptTitleLabel: formatAttemptLabelForTitle(attemptIndex, t),
    roleLabel: translateTimelineToken(t, 'roles', agentRole),
    scopeLabel: translateTimelineToken(t, 'scopes', timelineScope),
    phaseLabel: translateTimelineToken(t, 'phases', timelinePhase),
  }
}

function buildCanonicalTitle(item: OperationEventItem, context: CanonicalContext): string {
  const titleParts = uniqueParts([context.roleLabel, context.phaseLabel])
  const baseTitle = titleParts.length > 0
    ? titleParts.join(' · ')
    : (context.eventSummary || item.message || item.event_type)
  return withAttemptSuffix(baseTitle, context.attemptTitleLabel)
}

function buildCanonicalDescription(
  context: CanonicalContext,
  t: Translate,
  baseTitle: string,
): string | null {
  return uniqueParts([
    context.eventSummary && context.eventSummary !== baseTitle ? context.eventSummary : null,
    context.childOperationId ? t('runDetail.timeline.childOperationLabel', { operationId: context.childOperationId }) : null,
    context.parentOperationId && context.timelineScope === 'child_operation'
      ? t('runDetail.timeline.parentOperationLabel', { operationId: context.parentOperationId })
      : null,
  ]).join(' · ') || null
}

export function hasCanonicalTimelineFields(item: OperationEventItem): boolean {
  const record = asEventRecord(item)
  const data = asObject(item.data_json)
  return CANONICAL_PRESENCE_KEYS.some(key => readCanonicalStringField(record, data, key) != null)
}

export function presentCanonicalRunTimelineEvent(item: OperationEventItem, t: Translate): RunTimelineEventView {
  const context = buildCanonicalContext(item, t)
  const title = buildCanonicalTitle(item, context)
  const overrides = buildStructuredCanonicalOverrides(item, context.data, context.attemptTitleLabel, t)

  return {
    kind: 'default',
    title: overrides.title ?? title,
    description: overrides.description ?? buildCanonicalDescription(context, t, title),
    category: context.category,
    categoryLabel: context.categoryLabel,
    roleLabel: context.roleLabel,
    scopeLabel: context.scopeLabel,
    phaseLabel: context.phaseLabel,
    attemptLabel: context.attemptLabel,
    eventTypeLabel: item.event_type,
    rawData: context.data,
    detailRows: buildStructuredCanonicalDetails(item, context.data, t),
    failed: overrides.failed,
  }
}
