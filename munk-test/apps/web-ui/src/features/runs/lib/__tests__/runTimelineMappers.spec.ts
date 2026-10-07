import { describe, expect, it } from 'vitest'

import { presentRunTimelineEvent } from '@/features/runs/lib/runTimelineMappers'
import { i18n, setLocale } from '@/shared/i18n'
import type { OperationEventsData } from '@/shared/api/operations'

type OperationEventItem = NonNullable<OperationEventsData['items']>[number]

function t(key: string, params?: Record<string, unknown>): string {
  return i18n.global.t(key, params ?? {})
}

describe('presentRunTimelineEvent', () => {
  it('prefers canonical timeline fields when available', () => {
    setLocale('en-US')

    const item = {
      seq: 1,
      operation_id: 'op-1',
      event_type: 'child_operation_submitted',
      message: 'submitted optimize operation',
      timestamp: '2026-01-01T00:00:00Z',
      agent_role: 'optimize',
      timeline_scope: 'parent_run',
      timeline_phase: 'submitted',
      attempt_index: 0,
      child_operation_id: 'op-opt-1',
      summary: 'Submitted optimize follow-up operation.',
      data_json: {
        agent_role: 'runner',
        timeline_scope: 'child_operation',
        timeline_phase: 'failed',
      },
    } satisfies OperationEventItem

    const view = presentRunTimelineEvent(item, t)

    expect(view.title).toBe('Optimize · Submitted')
    expect(view.category).toBe('runtime')
    expect(view.roleLabel).toBe('Optimize')
    expect(view.scopeLabel).toBe('Parent Run')
    expect(view.phaseLabel).toBe('Submitted')
    expect(view.attemptLabel).toBe('Attempt 1')
    expect(view.description).toContain('Submitted optimize follow-up operation.')
    expect(view.description).toContain('Child operation: op-opt-1')
  })

  it('shows attempt suffix in canonical titles only from the second attempt onward', () => {
    setLocale('en-US')

    const item = {
      seq: 6,
      operation_id: 'op-1',
      event_type: 'runner_completed',
      message: 'runner completed',
      timestamp: '2026-01-01T00:00:05Z',
      agent_role: 'runner',
      timeline_scope: 'parent_run',
      timeline_phase: 'completed',
      attempt_index: 1,
      summary: 'Runner finished successfully.',
      data_json: {},
    } satisfies OperationEventItem

    const view = presentRunTimelineEvent(item, t)

    expect(view.title).toBe('Runner · Completed (Attempt 2)')
    expect(view.attemptLabel).toBe('Attempt 2')
  })

  it('falls back to legacy event_type mapping when canonical fields are absent', () => {
    setLocale('en-US')

    const item = {
      seq: 2,
      operation_id: 'op-1',
      event_type: 'workflow_retry_scheduled',
      message: 'judge requested another runner attempt',
      timestamp: '2026-01-01T00:00:01Z',
      data_json: {
        attempt_index: 0,
        retry_attempt: 1,
        retry_reason: 'Need a stable final screenshot',
      },
    } satisfies OperationEventItem

    const view = presentRunTimelineEvent(item, t)

    expect(view.title).toBe('Retry 1 scheduled')
    expect(view.category).toBe('orchestration')
    expect(view.scopeLabel).toBeNull()
    expect(view.phaseLabel).toBeNull()
    expect(view.description).toContain('Retry reason: Need a stable final screenshot')
  })

  it('falls back to prettified tokens for unknown canonical values', () => {
    setLocale('en-US')

    const item = {
      seq: 3,
      operation_id: 'op-1',
      event_type: 'custom_event',
      message: 'custom event',
      timestamp: '2026-01-01T00:00:02Z',
      agent_role: 'custom_agent',
      timeline_scope: 'child_operation',
      timeline_phase: 'result_ready',
      summary: 'Custom phase event.',
      data_json: {},
    } satisfies OperationEventItem

    const view = presentRunTimelineEvent(item, t)

    expect(view.title).toBe('Custom agent · Result Ready')
    expect(view.scopeLabel).toBe('Child Operation')
    expect(view.description).toBe('Custom phase event.')
  })

  it('builds dedicated LLM timeline views for request and response events', () => {
    setLocale('en-US')

    const requestItem = {
      seq: 4,
      operation_id: 'op-1',
      event_type: 'llm_request',
      message: 'runner llm request',
      timestamp: '2026-01-01T00:00:03Z',
      agent_role: 'runner',
      attempt_index: 0,
      data_json: {
        llm_provider: 'openai_compatible',
        llm_model: 'demo-model',
        llm_request_id: 'req-1',
        llm_text: 'SYSTEM\nrules\n\nUSER\nhello',
      },
    } satisfies OperationEventItem
    const responseItem = {
      seq: 5,
      operation_id: 'op-1',
      event_type: 'llm_response',
      message: 'runner llm response',
      timestamp: '2026-01-01T00:00:04Z',
      agent_role: 'judge',
      attempt_index: 0,
      data_json: {
        llm_provider: 'openai_compatible',
        llm_model: 'demo-model',
        llm_request_id: 'req-1',
        llm_status_code: 200,
        llm_text: 'Reasoning\nThink\n\nResponse\nDone',
      },
    } satisfies OperationEventItem

    const requestView = presentRunTimelineEvent(requestItem, t)
    const responseView = presentRunTimelineEvent(responseItem, t)

    expect(requestView.kind).toBe('llm')
    expect(requestView.title).toBe('Runner Request')
    expect(requestView.llmPreviewText).toContain('SYSTEM')
    expect(requestView.description).toContain('openai_compatible / demo-model')

    expect(responseView.kind).toBe('llm')
    expect(responseView.title).toBe('Judge Response')
    expect(responseView.llmStatusCode).toBe(200)
    expect(responseView.description).toContain('Status code: 200')
  })

  it('surfaces structured batch details instead of only raw data', () => {
    setLocale('en-US')

    const item = {
      seq: 7,
      operation_id: 'op-1',
      event_type: 'batch_child_finished',
      message: 'plan child case finished',
      timestamp: '2026-01-01T00:00:06Z',
      agent_role: 'runner',
      timeline_scope: 'parent_run',
      timeline_phase: 'completed',
      summary: 'Finished executing child case.',
      data_json: {
        operation_id: 'op-child-1',
        case_id: 'case-1',
        title: 'Checkout flow',
        status: 'succeeded',
        verification_verdict: 'passed',
        position_label: '1/3',
      },
    } satisfies OperationEventItem

    const view = presentRunTimelineEvent(item, t)

    expect(view.title).toBe('Case Finished')
    expect(view.detailRows).toEqual(
      expect.arrayContaining([
        { label: 'Case ID', value: 'case-1' },
        { label: 'Title', value: 'Checkout flow' },
        { label: 'Status', value: 'succeeded' },
        { label: 'Verdict', value: 'passed' },
      ]),
    )
  })

  it('surfaces structured planning and review details', () => {
    setLocale('en-US')

    const planningItem = {
      seq: 8,
      operation_id: 'op-1',
      event_type: 'change_verification_plan_saved',
      message: 'change verification plan saved',
      timestamp: '2026-01-01T00:00:07Z',
      agent_role: 'planner',
      timeline_scope: 'parent_run',
      timeline_phase: 'completed',
      data_json: {
        app_id: 'app-1',
        plan_id: 'plan-1',
        case_count: 3,
        plan_path: '/tmp/plan.json',
      },
    } satisfies OperationEventItem
    const reviewItem = {
      seq: 9,
      operation_id: 'op-1',
      event_type: 'review_retrieval_completed',
      message: 'review retrieval completed',
      timestamp: '2026-01-01T00:00:08Z',
      agent_role: 'review',
      timeline_scope: 'parent_run',
      timeline_phase: 'running',
      data_json: {
        app_id: 'app-1',
        retrieval_hit_count: 8,
        prompt_hit_count: 4,
      },
    } satisfies OperationEventItem

    const planningView = presentRunTimelineEvent(planningItem, t)
    const reviewView = presentRunTimelineEvent(reviewItem, t)

    expect(planningView.title).toBe('Verification Plan Saved')
    expect(planningView.detailRows).toEqual(
      expect.arrayContaining([
        { label: 'Plan ID', value: 'plan-1' },
        { label: 'Case count', value: '3' },
      ]),
    )
    expect(reviewView.title).toBe('Review Retrieval Completed')
    expect(reviewView.detailRows).toEqual(
      expect.arrayContaining([
        { label: 'Retrieval hits', value: '8' },
        { label: 'Prompt hits', value: '4' },
      ]),
    )
  })

  it('surfaces structured knowledge details', () => {
    setLocale('en-US')

    const item = {
      seq: 10,
      operation_id: 'op-1',
      event_type: 'knowledge_prompt_ready',
      message: 'knowledge prompt ready',
      timestamp: '2026-01-01T00:00:09Z',
      agent_role: 'knowledge',
      timeline_scope: 'child_operation',
      timeline_phase: 'prompt_ready',
      data_json: {
        prompt_path: '/tmp/knowledge_prompt.txt',
        tool_call_count: 2,
      },
    } satisfies OperationEventItem

    const view = presentRunTimelineEvent(item, t)

    expect(view.title).toBe('Knowledge Prompt Ready')
    expect(view.detailRows).toEqual(
      expect.arrayContaining([
        { label: 'Prompt path', value: '/tmp/knowledge_prompt.txt' },
        { label: 'Tool calls', value: '2' },
      ]),
    )
  })

  it('surfaces structured optimize details', () => {
    setLocale('en-US')

    const item = {
      seq: 11,
      operation_id: 'op-1',
      event_type: 'optimize_applied',
      message: 'ai_guidance fields updated',
      timestamp: '2026-01-01T00:00:10Z',
      agent_role: 'optimize',
      timeline_scope: 'child_operation',
      timeline_phase: 'applied',
      data_json: {
        patched_fields: ['judge_hints', 'expected'],
        applied: true,
      },
    } satisfies OperationEventItem

    const view = presentRunTimelineEvent(item, t)

    expect(view.title).toBe('Optimize Applied')
    expect(view.detailRows).toEqual(
      expect.arrayContaining([
        { label: 'Patched fields', value: 'judge_hints, expected' },
        { label: 'Applied', value: 'Yes' },
      ]),
    )
  })

  it('surfaces knowledge tool call details', () => {
    setLocale('en-US')

    const item = {
      seq: 12,
      operation_id: 'op-1',
      event_type: 'knowledge_tool_called',
      message: 'knowledge tool called: read_judge_result',
      timestamp: '2026-01-01T00:00:11Z',
      agent_role: 'knowledge',
      timeline_scope: 'child_operation',
      timeline_phase: 'tool_called',
      data_json: {
        tool_name: 'read_judge_result',
        tool_index: 0,
      },
    } satisfies OperationEventItem

    const view = presentRunTimelineEvent(item, t)

    expect(view.title).toBe('Knowledge Tool Called')
    expect(view.detailRows).toEqual(
      expect.arrayContaining([
        { label: 'Tool', value: 'read_judge_result' },
        { label: 'Tool index', value: '0' },
      ]),
    )
  })

  it('routes context prepare setup step events to setup presenter', () => {
    setLocale('en-US')

    const item = {
      seq: 14,
      operation_id: 'op-1',
      event_type: 'context_prepare_setup_step',
      message: 'context prepare setup step 1/1',
      timestamp: '2026-01-01T00:00:12Z',
      agent_role: 'context_prepare',
      timeline_scope: 'parent_run',
      timeline_phase: 'prepared',
      attempt_index: 0,
      summary: 'GET test_backend /api/seed → 200',
      data_json: {
        step_index: 0,
        step_total: 1,
        step_kind: 'http',
        outcome: 'succeeded',
        duration_ms: 12,
        method: 'GET',
        base: 'test_backend',
        path: '/api/seed',
        status_code: 200,
        response_body: '{"ok":true}',
      },
    } satisfies OperationEventItem

    const view = presentRunTimelineEvent(item, t)

    expect(view.kind).toBe('setup_step')
    expect(view.title).toContain('GET test_backend/api/seed → 200')
    expect(view.setupSections?.some(section => section.id === 'response_body')).toBe(true)
  })

  it('routes context prepare start state step events to start state presenter', () => {
    setLocale('en-US')

    const item = {
      seq: 15,
      operation_id: 'op-1',
      event_type: 'context_prepare_start_state_step',
      message: 'context prepare start state step 1/2',
      timestamp: '2026-01-01T00:00:13Z',
      agent_role: 'context_prepare',
      timeline_scope: 'parent_run',
      timeline_phase: 'prepared',
      attempt_index: 0,
      summary: 'unlock device → unlocked',
      data_json: {
        step_index: 0,
        step_total: 2,
        step_kind: 'unlock',
        outcome: 'succeeded',
        duration_ms: 6,
      },
    } satisfies OperationEventItem

    const view = presentRunTimelineEvent(item, t)

    expect(view.kind).toBe('start_state_step')
    expect(view.title).toBe('Unlock device')
    expect(view.description).toContain('Succeeded')
  })

  it('surfaces optimize generated result details', () => {
    setLocale('en-US')

    const item = {
      seq: 13,
      operation_id: 'op-1',
      event_type: 'optimize_result_generated',
      message: 'optimize result generated',
      timestamp: '2026-01-01T00:00:12Z',
      agent_role: 'optimize',
      timeline_scope: 'child_operation',
      timeline_phase: 'result_generated',
      data_json: {
        patched_fields: ['judge_hints'],
        patched_field_summaries: ['judge_hints: clarify end-state wording'],
        patched_field_count: 1,
      },
    } satisfies OperationEventItem

    const view = presentRunTimelineEvent(item, t)

    expect(view.title).toBe('Optimize Result Generated')
    expect(view.detailRows).toEqual(
      expect.arrayContaining([
        { label: 'Patched fields', value: 'judge_hints' },
        { label: 'Patch summary', value: 'judge_hints: clarify end-state wording' },
        { label: 'Patched count', value: '1' },
      ]),
    )
  })

  it('does not duplicate request path in optimize details', () => {
    setLocale('en-US')

    const item = {
      seq: 14,
      operation_id: 'op-1',
      event_type: 'optimize_request_built',
      message: 'optimize request built',
      timestamp: '2026-01-01T00:00:13Z',
      agent_role: 'optimize',
      timeline_scope: 'child_operation',
      timeline_phase: 'context_loaded',
      data_json: {
        request_path: '/tmp/optimize_request.json',
      },
    } satisfies OperationEventItem

    const view = presentRunTimelineEvent(item, t)
    const requestRows = view.detailRows.filter(row => row.label === 'Request path')

    expect(requestRows).toEqual([{ label: 'Request path', value: '/tmp/optimize_request.json' }])
  })

  it('surfaces pre-execute invalidation details on action proposals', () => {
    setLocale('en-US')

    const item = {
      seq: 15,
      operation_id: 'op-1',
      event_type: 'action_proposed',
      message: 'runner proposed click action',
      timestamp: '2026-01-01T00:00:14Z',
      agent_role: 'runner',
      timeline_scope: 'parent_run',
      timeline_phase: 'running',
      summary: 'Proposed tapping the checkout button.',
      data_json: {
        action: 'click',
        summary: 'Tap Checkout',
        pre_execute_status: 'invalidated',
        pre_execute_invalidated: true,
        stale_reason: 'stable_key_missing',
        target_match_strategy: 'stable_key',
        target_stable_key: 'checkout_button',
      },
    } satisfies OperationEventItem

    const view = presentRunTimelineEvent(item, t)

    expect(view.description).toBe('Proposal invalidated before execution. · stable_key_missing')
    expect(view.detailRows).toEqual(
      expect.arrayContaining([
        { label: 'Pre-execute status', value: 'Invalidated' },
        { label: 'Stale reason', value: 'stable_key_missing' },
        { label: 'Target match strategy', value: 'stable_key' },
        { label: 'Target stable key', value: 'checkout_button' },
      ]),
    )
  })

  it('surfaces pre-execute rebound details on action execution start', () => {
    setLocale('en-US')

    const item = {
      seq: 16,
      operation_id: 'op-1',
      event_type: 'action_execution_started',
      message: 'runner started action execution',
      timestamp: '2026-01-01T00:00:15Z',
      agent_role: 'runner',
      timeline_scope: 'parent_run',
      timeline_phase: 'running',
      summary: 'Started executing tap action.',
      data_json: {
        action: 'click',
        summary: 'Tap Checkout',
        pre_execute_status: 'matched',
        pre_execute_rebound: true,
        target_match_strategy: 'resource_id',
        target_stable_key: 'checkout_button',
      },
    } satisfies OperationEventItem

    const view = presentRunTimelineEvent(item, t)

    expect(view.description).toBe('Target rebound on fresh screen before execution. · resource_id')
    expect(view.detailRows).toEqual(
      expect.arrayContaining([
        { label: 'Pre-execute status', value: 'Matched' },
        { label: 'Pre-execute rebound', value: 'Yes' },
        { label: 'Target match strategy', value: 'resource_id' },
        { label: 'Target stable key', value: 'checkout_button' },
      ]),
    )
  })

  it('surfaces passthrough status without showing rebound no', () => {
    setLocale('en-US')

    const item = {
      seq: 17,
      operation_id: 'op-1',
      event_type: 'action_execution_started',
      message: 'runner started action execution',
      timestamp: '2026-01-01T00:00:16Z',
      agent_role: 'runner',
      timeline_scope: 'parent_run',
      timeline_phase: 'running',
      summary: 'Started executing tap action.',
      data_json: {
        action: 'click',
        summary: 'Tap Task Title',
        pre_execute_status: 'passthrough',
        pre_execute_rebound: false,
      },
    } satisfies OperationEventItem

    const view = presentRunTimelineEvent(item, t)

    expect(view.description).toBe('Target passed through without structured pre-execute match.')
    expect(view.detailRows).toEqual(
      expect.arrayContaining([
        { label: 'Pre-execute status', value: 'Passthrough' },
      ]),
    )
    expect(view.detailRows.find(row => row.label === 'Pre-execute rebound')).toBeUndefined()
  })
})
