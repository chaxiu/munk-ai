import { describe, expect, it } from 'vitest'

import { presentSetupStepRunTimelineEvent } from '@/features/runs/lib/runTimelineSetup'
import { i18n, setLocale } from '@/shared/i18n'
import type { OperationEventsData } from '@/shared/api/operations'

type OperationEventItem = NonNullable<OperationEventsData['items']>[number]

function t(key: string, params?: Record<string, unknown>): string {
  return i18n.global.t(key, params ?? {})
}

describe('presentSetupStepRunTimelineEvent', () => {
  it('maps successful http setup step with collapsible sections', () => {
    setLocale('en-US')

    const item = {
      seq: 10,
      operation_id: 'op-1',
      event_type: 'context_prepare_setup_step',
      message: 'context prepare setup step 1/2',
      timestamp: '2026-01-01T00:00:10Z',
      agent_role: 'context_prepare',
      timeline_scope: 'parent_run',
      timeline_phase: 'prepared',
      attempt_index: 0,
      summary: 'POST test_backend /api/seed → 200',
      data_json: {
        agent_role: 'context_prepare',
        step_index: 0,
        step_total: 2,
        step_kind: 'http',
        outcome: 'succeeded',
        duration_ms: 18,
        method: 'POST',
        base: 'test_backend',
        path: '/api/seed',
        request_body: { count: 2 },
        status_code: 200,
        response_body: '{"ok":true}',
      },
    } satisfies OperationEventItem

    const view = presentSetupStepRunTimelineEvent(item, t)

    expect(view.kind).toBe('setup_step')
    expect(view.failed).toBe(false)
    expect(view.title).toContain('POST test_backend/api/seed → 200')
    expect(view.description).toContain('18 ms')
    expect(view.description).toContain('Succeeded')
    expect(view.setupSections?.map(section => section.id)).toEqual([
      'request_body',
      'response_body',
    ])
    expect(view.setupSections?.[0]?.fullText).toBe('{\n  "count": 2\n}')
    expect(view.setupSections?.[1]?.fullText).toBe('{"ok":true}')
  })

  it('maps failed command setup step with stderr section', () => {
    setLocale('en-US')

    const item = {
      seq: 11,
      operation_id: 'op-1',
      event_type: 'context_prepare_setup_step',
      message: 'context prepare setup step 2/2',
      timestamp: '2026-01-01T00:00:11Z',
      agent_role: 'context_prepare',
      timeline_scope: 'parent_run',
      timeline_phase: 'prepared',
      attempt_index: 0,
      summary: 'echo hello → exit 1 (failed)',
      data_json: {
        agent_role: 'context_prepare',
        step_index: 1,
        step_total: 2,
        step_kind: 'command',
        outcome: 'failed',
        duration_ms: 5,
        exec: 'echo',
        args: ['hello'],
        exit_code: 1,
        expected_exit_code: 0,
        stderr_tail: 'failed',
        error_message: 'setup step 2 command failed',
      },
    } satisfies OperationEventItem

    const view = presentSetupStepRunTimelineEvent(item, t)

    expect(view.failed).toBe(true)
    expect(view.title).toContain('(failed)')
    expect(view.defaultExpandedSectionIds).toEqual(['error_message'])
    expect(view.setupSections?.map(section => section.id)).toEqual([
      'stderr_tail',
      'error_message',
    ])
    expect(view.setupSections?.find(section => section.id === 'stderr_tail')?.fullText).toBe('failed')
  })
})
