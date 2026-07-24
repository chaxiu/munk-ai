import { describe, expect, it } from 'vitest'

import { presentStartStateStepRunTimelineEvent } from '@/features/runs/lib/runTimelineStartState'
import { i18n, setLocale } from '@/shared/i18n'
import type { OperationEventsData } from '@/shared/api/operations'

type OperationEventItem = NonNullable<OperationEventsData['items']>[number]

function t(key: string, params?: Record<string, unknown>): string {
  return i18n.global.t(key, params ?? {})
}

describe('presentStartStateStepRunTimelineEvent', () => {
  it('maps successful app reset step', () => {
    setLocale('en-US')

    const item = {
      seq: 12,
      operation_id: 'op-1',
      event_type: 'context_prepare_start_state_step',
      message: 'context prepare start state step 2/2',
      timestamp: '2026-01-01T00:00:12Z',
      agent_role: 'context_prepare',
      timeline_scope: 'parent_run',
      timeline_phase: 'prepared',
      attempt_index: 0,
      summary: 'reset com.test.app → stop + start',
      data_json: {
        step_index: 1,
        step_total: 2,
        step_kind: 'app_reset',
        outcome: 'succeeded',
        duration_ms: 14,
        start_mode: 'reset',
        entry_identity: 'com.test.app',
      },
    } satisfies OperationEventItem

    const view = presentStartStateStepRunTimelineEvent(item, t)

    expect(view.kind).toBe('start_state_step')
    expect(view.failed).toBe(false)
    expect(view.skipped).toBe(false)
    expect(view.title).toBe('Reset com.test.app')
    expect(view.description).toContain('14 ms')
    expect(view.description).toContain('Succeeded')
    expect(view.startStateSections).toEqual([])
  })

  it('maps skipped unlock step with skip reason section', () => {
    setLocale('en-US')

    const item = {
      seq: 13,
      operation_id: 'op-1',
      event_type: 'context_prepare_start_state_step',
      message: 'context prepare start state step 1/2',
      timestamp: '2026-01-01T00:00:13Z',
      agent_role: 'context_prepare',
      timeline_scope: 'parent_run',
      timeline_phase: 'prepared',
      attempt_index: 0,
      summary: 'unlock device → skipped (already_unlocked)',
      data_json: {
        step_index: 0,
        step_total: 2,
        step_kind: 'unlock',
        outcome: 'skipped',
        duration_ms: 1,
        skip_reason: 'already_unlocked',
        was_locked: false,
      },
    } satisfies OperationEventItem

    const view = presentStartStateStepRunTimelineEvent(item, t)

    expect(view.skipped).toBe(true)
    expect(view.title).toBe('Unlock device (skipped)')
    expect(view.description).toContain('Skipped')
    expect(view.description).toContain('Already unlocked')
    expect(view.startStateSections?.map(section => section.id)).toEqual(['skip_reason'])
  })

  it('maps failed page navigation step with error section', () => {
    setLocale('en-US')

    const item = {
      seq: 14,
      operation_id: 'op-1',
      event_type: 'context_prepare_start_state_step',
      message: 'context prepare start state step 3/3',
      timestamp: '2026-01-01T00:00:14Z',
      agent_role: 'context_prepare',
      timeline_scope: 'parent_run',
      timeline_phase: 'prepared',
      attempt_index: 0,
      summary: 'navigate to task_edit → failed',
      data_json: {
        step_index: 2,
        step_total: 3,
        step_kind: 'page_navigation',
        outcome: 'failed',
        duration_ms: 2,
        page_id: 'task_edit',
        app_id: 'app-1',
        error_message: 'requires a registered page navigator',
      },
    } satisfies OperationEventItem

    const view = presentStartStateStepRunTimelineEvent(item, t)

    expect(view.failed).toBe(true)
    expect(view.title).toBe('Navigate to task_edit (failed)')
    expect(view.startStateSections?.map(section => section.id)).toEqual(['error_message'])
    expect(view.startStateSections?.[0]?.fullText).toBe('requires a registered page navigator')
  })
})
