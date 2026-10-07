import { describe, expect, it } from 'vitest'

import { knowledgePostActionResult } from '@/features/runs/lib/runSummaryMappers'
import type { OperationDetailData } from '@/shared/api/operations'

function buildOperationDetail(overrides: Partial<OperationDetailData>): OperationDetailData {
  return {
    operation_id: 'op-1',
    kind: 'run_case',
    cancel_requested: false,
    created_at: '2024-01-01T00:00:00Z',
    is_batch: false,
    status: 'succeeded',
    ...overrides,
  }
}

function buildKnowledgeDetail(result: OperationDetailData['result']): OperationDetailData {
  return buildOperationDetail({
    operation_id: 'op-knowledge-1',
    kind: 'knowledge_post_action',
    run_type: 'knowledge_post_action',
    title: 'Knowledge post action',
    app_id: 'demo-app',
    result,
  })
}

describe('knowledgePostActionResult', () => {
  it('returns null for non knowledge post-action runs', () => {
    const detail = buildOperationDetail({
      run_type: 'case_run',
      result: { submitted: true } as unknown as OperationDetailData['result'],
    })

    expect(knowledgePostActionResult(detail)).toBeNull()
  })

  it('parses submitted knowledge post-action result', () => {
    const detail = buildKnowledgeDetail({
      summary: 'candidate generated',
      submitted: true,
      skip_reason: null,
      candidate_id: 'candidate-1',
      knowledge_post_action_result_path: '/tmp/result.json',
      knowledge_post_action_request_path: '/tmp/request.json',
      knowledge_post_action_diagnostics_path: '/tmp/diagnostics.json',
      knowledge_post_action_tool_calls_path: '/tmp/tool-calls.json',
      artifacts: {},
    } as unknown as OperationDetailData['result'])

    expect(knowledgePostActionResult(detail)).toEqual({
      summary: 'candidate generated',
      submitted: true,
      skipReason: null,
      candidateId: 'candidate-1',
    })
  })

  it('parses skipped knowledge post-action result', () => {
    const detail = buildKnowledgeDetail({
      summary: 'knowledge post action skipped: passed case',
      submitted: false,
      skip_reason: 'verdict_passed',
      candidate_id: null,
      knowledge_post_action_result_path: '/tmp/result.json',
      knowledge_post_action_request_path: '/tmp/request.json',
      knowledge_post_action_diagnostics_path: '/tmp/diagnostics.json',
      knowledge_post_action_tool_calls_path: '/tmp/tool-calls.json',
      artifacts: {},
    } as unknown as OperationDetailData['result'])

    expect(knowledgePostActionResult(detail)).toEqual({
      summary: 'knowledge post action skipped: passed case',
      submitted: false,
      skipReason: 'verdict_passed',
      candidateId: null,
    })
  })
})
