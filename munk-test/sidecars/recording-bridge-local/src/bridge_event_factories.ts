import type { ScrcpyMediaStreamPacket, ScrcpyVideoStreamMetadata } from '@yume-chan/scrcpy'

import type {
  BridgeBackForwardingAckEvent,
  BridgeErrorEvent,
  BridgeHelloEvent,
  BridgeInputForwardingAckEvent,
  BridgeKeyPressForwardingStep,
  BridgeKeyTransitionForwardingStep,
  BridgePacketConfigurationEvent,
  BridgePacketDataEvent,
  BridgePointerForwardingAckEvent,
  BridgePointerForwardingStep,
  BridgeTextInjectForwardingStep
} from './protocol.js'
import { toBase64 } from './protocol.js'

export function buildHelloEvent (
  recordingId: string,
  metadata: ScrcpyVideoStreamMetadata
): BridgeHelloEvent {
  return {
    type: 'hello',
    recordingId,
    codec: metadata.codec,
    deviceName: metadata.deviceName,
    width: metadata.width,
    height: metadata.height
  }
}

export function buildPacketConfigurationEvent (
  packet: Extract<ScrcpyMediaStreamPacket, { type: 'configuration' }>
): BridgePacketConfigurationEvent {
  return {
    type: 'packet_configuration',
    dataBase64: toBase64(packet.data)
  }
}

export function buildPacketDataEvent (
  packet: Exclude<ScrcpyMediaStreamPacket, { type: 'configuration' }>
): BridgePacketDataEvent {
  return {
    type: 'packet_data',
    dataBase64: toBase64(packet.data),
    keyframe: packet.keyframe,
    pts: packet.pts?.toString()
  }
}

export function buildVideoStreamErrorEvent (error: unknown): BridgeErrorEvent {
  return {
    type: 'error',
    code: 'video_stream_failed',
    message: error instanceof Error ? error.message : String(error)
  }
}

export function buildPointerStep (
  seq: number,
  stepKind: BridgePointerForwardingStep['stepKind'],
  payload: BridgePointerForwardingStep['payload']
): BridgePointerForwardingStep {
  return {
    seq,
    stepKind,
    payload,
    dispatchedAt: new Date().toISOString()
  }
}

export function buildTextInjectStep (
  seq: number,
  payload: BridgeTextInjectForwardingStep['payload']
): BridgeTextInjectForwardingStep {
  return {
    seq,
    stepKind: 'text_inject',
    payload,
    dispatchedAt: new Date().toISOString()
  }
}

export function buildKeyPressStep (
  seq: number,
  payload: BridgeKeyPressForwardingStep['payload']
): BridgeKeyPressForwardingStep {
  return {
    seq,
    stepKind: 'key_press',
    payload,
    dispatchedAt: new Date().toISOString()
  }
}

export function buildKeyTransitionStep (
  seq: number,
  stepKind: BridgeKeyTransitionForwardingStep['stepKind'],
  payload: BridgeKeyTransitionForwardingStep['payload']
): BridgeKeyTransitionForwardingStep {
  return {
    seq,
    stepKind,
    payload,
    dispatchedAt: new Date().toISOString()
  }
}

export function buildPointerAck (
  clientCommandId: string,
  payload: BridgePointerForwardingAckEvent['payload'],
  steps: BridgePointerForwardingAckEvent['steps']
): BridgePointerForwardingAckEvent {
  return {
    type: 'forwarding_ack',
    clientCommandId,
    kind: 'pointer',
    ackAt: new Date().toISOString(),
    payload,
    steps,
    deviceResult: { ok: true }
  }
}

export function buildInputAck (
  clientCommandId: string,
  payload: BridgeInputForwardingAckEvent['payload'],
  steps: BridgeInputForwardingAckEvent['steps']
): BridgeInputForwardingAckEvent {
  return {
    type: 'forwarding_ack',
    clientCommandId,
    kind: 'input',
    ackAt: new Date().toISOString(),
    payload,
    steps,
    deviceResult: { ok: true }
  }
}

export function buildBackAck (
  clientCommandId: string,
  steps: BridgeBackForwardingAckEvent['steps']
): BridgeBackForwardingAckEvent {
  return {
    type: 'forwarding_ack',
    clientCommandId,
    kind: 'back',
    ackAt: new Date().toISOString(),
    payload: {},
    steps,
    deviceResult: { ok: true }
  }
}
