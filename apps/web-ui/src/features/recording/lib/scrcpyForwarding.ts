import type { BridgeForwardingAckEvent, BridgeForwardingStep } from '../types'
import type { ForwardingAckRequest } from '@/shared/api/recording'

function mapForwardingSteps(steps: BridgeForwardingStep[]) {
  return steps.map((step) => ({
    seq: step.seq,
    step_kind: step.stepKind,
    payload: step.payload,
    dispatched_at: step.dispatchedAt
  }))
}

export function mapForwardingAckEvent(event: BridgeForwardingAckEvent): ForwardingAckRequest {
  const base = {
    kind: event.kind,
    dispatched_at: event.dispatchedAt,
    ack_at: event.ackAt,
    device_result: event.deviceResult
  } as const

  if (event.kind === 'pointer') {
    return {
      ...base,
      kind: 'pointer',
      payload: event.payload,
      steps: mapForwardingSteps(event.steps)
    }
  }

  if (event.kind === 'input') {
    return {
      ...base,
      kind: 'input',
      payload: event.payload,
      steps: mapForwardingSteps(event.steps)
    }
  }

  return {
    ...base,
    kind: 'back',
    payload: event.payload,
    steps: mapForwardingSteps(event.steps)
  }
}
