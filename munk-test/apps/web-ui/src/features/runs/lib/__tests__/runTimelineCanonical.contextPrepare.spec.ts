import { describe, expect, it } from 'vitest'

import { presentCanonicalRunTimelineEvent } from '@/features/runs/lib/runTimelineCanonical'
import type { OperationEventsData } from '@/shared/api/operations'
import { i18n, setLocale } from '@/shared/i18n'

type OperationEventItem = NonNullable<OperationEventsData['items']>[number]

function t(key: string, params?: Record<string, unknown>): string {
  return i18n.global.t(key, params ?? {})
}

describe('runTimelineCanonical context prepare', () => {
  it('maps context_prepare boundary titles with i18n', () => {
    setLocale('en-US')

    const started = presentCanonicalRunTimelineEvent({
      seq: 1,
      operation_id: 'op-1',
      event_type: 'context_prepare_started',
      message: 'context prepare started',
      timestamp: '2026-01-01T00:00:01Z',
      agent_role: 'context_prepare',
      timeline_scope: 'parent_run',
      timeline_phase: 'started',
      summary: 'context prepare started',
      data_json: {
        agent_role: 'context_prepare',
        timeline_scope: 'parent_run',
        timeline_phase: 'started',
        summary: 'context prepare started',
      },
    } satisfies OperationEventItem, t)

    expect(started.title).toBe('Context Prepare Started')
    expect(started.failed).toBeUndefined()

    const setupReady = presentCanonicalRunTimelineEvent({
      seq: 2,
      operation_id: 'op-1',
      event_type: 'context_prepare_setup_ready',
      message: 'context prepare setup completed',
      timestamp: '2026-01-01T00:00:02Z',
      agent_role: 'context_prepare',
      timeline_scope: 'parent_run',
      timeline_phase: 'prepared',
      summary: 'case setup completed',
      data_json: {
        agent_role: 'context_prepare',
        step_count: 2,
        duration_ms: 45,
      },
    } satisfies OperationEventItem, t)

    expect(setupReady.title).toBe('Case Setup Ready')
    expect(setupReady.detailRows.some(row => row.label === 'Step count' && row.value === '2')).toBe(true)
    expect(setupReady.detailRows.some(row => row.label === 'Duration (ms)' && row.value === '45')).toBe(true)
  })

  it('maps context_prepare_failed with failed styling and detail rows', () => {
    setLocale('en-US')

    const view = presentCanonicalRunTimelineEvent({
      seq: 3,
      operation_id: 'op-1',
      event_type: 'context_prepare_failed',
      message: 'context prepare failed: setup step 1 failed',
      timestamp: '2026-01-01T00:00:03Z',
      agent_role: 'context_prepare',
      timeline_scope: 'parent_run',
      timeline_phase: 'failed',
      summary: 'context prepare failed',
      data_json: {
        agent_role: 'context_prepare',
        timeline_scope: 'parent_run',
        timeline_phase: 'failed',
        failed_phase: 'setup',
        error_type: 'SetupExecutionError',
        error_message: 'setup step 1 failed',
        step_index: 0,
      },
    } satisfies OperationEventItem, t)

    expect(view.title).toBe('Context Prepare Failed')
    expect(view.failed).toBe(true)
    expect(view.description).toContain('Setup')
    expect(view.description).toContain('setup step 1 failed')
    expect(view.detailRows.some(row => row.label === 'Failed phase' && row.value === 'Setup')).toBe(true)
    expect(view.detailRows.some(row => row.label === 'Error type' && row.value === 'SetupExecutionError')).toBe(true)
    expect(view.detailRows.some(row => row.label === 'Step index' && row.value === '0')).toBe(true)
  })

  it('maps context_prepare_params_resolved detail rows', () => {
    setLocale('zh-CN')

    const view = presentCanonicalRunTimelineEvent({
      seq: 4,
      operation_id: 'op-1',
      event_type: 'context_prepare_params_resolved',
      message: 'context prepare resolved runtime params',
      timestamp: '2026-01-01T00:00:04Z',
      agent_role: 'context_prepare',
      timeline_scope: 'parent_run',
      timeline_phase: 'prepared',
      summary: 'runtime params resolved',
      data_json: {
        agent_role: 'context_prepare',
        device_ref: 'device-1',
        max_steps: 20,
        settle_mode: 'ocr',
      },
    } satisfies OperationEventItem, t)

    expect(view.title).toBe('运行时参数已解析')
    expect(view.detailRows.some(row => row.label === '设备' && row.value === 'device-1')).toBe(true)
    expect(view.detailRows.some(row => row.label === '最大步数' && row.value === '20')).toBe(true)
    expect(view.detailRows.some(row => row.label === '稳定模式' && row.value === 'ocr')).toBe(true)
  })
})
