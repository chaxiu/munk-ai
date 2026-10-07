import { describe, expect, it } from 'vitest'

import { presentJudgeEvidenceItems } from '@/features/runs/lib/runEvidenceMappers'
import type { Translate } from '@/features/runs/lib/runMapperShared'
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

const t: Translate = (key) => key

describe('presentJudgeEvidenceItems', () => {
  it('keeps decision_trace payload as raw payload for evidence preview', () => {
    const detail = buildOperationDetail({
      result: {
        evidence: [
          {
            evidence_id: 'trace-7',
            kind: 'decision_trace',
            source: 'artifact',
            summary: '[SCREEN] target_identity=demo.target surface_identity=demo.surface elements=25',
            payload: {
              path: '/tmp/run-1/decision_trace.jsonl',
              step_index: 4,
              action: 'tap',
              arguments: {
                target: 'Settings',
              },
              raw_line: '{"action":"tap"}',
            },
          },
        ],
      } as unknown as OperationDetailData['result'],
    })

    expect(presentJudgeEvidenceItems(detail, t)).toEqual([
      expect.objectContaining({
        evidenceId: 'trace-7',
        path: '/tmp/run-1/decision_trace.jsonl',
        stepIndex: 4,
        rawPayload: {
          path: '/tmp/run-1/decision_trace.jsonl',
          step_index: 4,
          action: 'tap',
          arguments: {
            target: 'Settings',
          },
          raw_line: '{"action":"tap"}',
        },
      }),
    ])
  })
})
