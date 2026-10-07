export interface BridgeHelloEvent {
  type: 'hello'
  recordingId: string
  codec: number
  deviceName?: string
  width?: number
  height?: number
}

export interface BridgePacketConfigurationEvent {
  type: 'packet_configuration'
  dataBase64: string
}

export interface BridgePacketDataEvent {
  type: 'packet_data'
  dataBase64: string
  pts?: string
  keyframe?: boolean
}

export interface BridgeSizeChangedEvent {
  type: 'size_changed'
  width: number
  height: number
}

export interface BridgeForwardingDeviceResult {
  ok: boolean
  error_code?: string
  message?: string
}

export interface BridgePointerForwardingPayload {
  pointer_id: number
  start_x: number
  start_y: number
  end_x: number
  end_y: number
  width: number
  height: number
}

export interface BridgeInputForwardingPayload {
  text: string
  submit: boolean
}

export type BridgeBackForwardingPayload = Record<string, never>

export interface BridgePointerStepPayload {
  pointer_id: number
  x: number
  y: number
}

export interface BridgeTextInjectStepPayload {
  text: string
  submit: boolean
}

export interface BridgeKeyPressStepPayload {
  key: string
}

export interface BridgeKeyTransitionStepPayload {
  key: string
}

export interface BridgePointerForwardingStep {
  seq: number
  stepKind: 'pointer_down' | 'pointer_move' | 'pointer_up'
  payload: BridgePointerStepPayload
  dispatchedAt: string
}

export interface BridgeTextInjectForwardingStep {
  seq: number
  stepKind: 'text_inject'
  payload: BridgeTextInjectStepPayload
  dispatchedAt: string
}

export interface BridgeKeyPressForwardingStep {
  seq: number
  stepKind: 'key_press'
  payload: BridgeKeyPressStepPayload
  dispatchedAt: string
}

export interface BridgeKeyTransitionForwardingStep {
  seq: number
  stepKind: 'key_down' | 'key_up'
  payload: BridgeKeyTransitionStepPayload
  dispatchedAt: string
}

export type BridgeForwardingStep =
  | BridgePointerForwardingStep
  | BridgeTextInjectForwardingStep
  | BridgeKeyPressForwardingStep
  | BridgeKeyTransitionForwardingStep

export interface BridgePointerForwardingAckEvent {
  type: 'forwarding_ack'
  clientCommandId: string
  kind: 'pointer'
  ackAt: string
  dispatchedAt?: string
  payload: BridgePointerForwardingPayload
  steps: BridgePointerForwardingStep[]
  deviceResult: BridgeForwardingDeviceResult
}

export interface BridgeInputForwardingAckEvent {
  type: 'forwarding_ack'
  clientCommandId: string
  kind: 'input'
  ackAt: string
  dispatchedAt?: string
  payload: BridgeInputForwardingPayload
  steps: Array<BridgeTextInjectForwardingStep | BridgeKeyPressForwardingStep>
  deviceResult: BridgeForwardingDeviceResult
}

export interface BridgeBackForwardingAckEvent {
  type: 'forwarding_ack'
  clientCommandId: string
  kind: 'back'
  ackAt: string
  dispatchedAt?: string
  payload: BridgeBackForwardingPayload
  steps: BridgeKeyTransitionForwardingStep[]
  deviceResult: BridgeForwardingDeviceResult
}

export type BridgeForwardingAckEvent =
  | BridgePointerForwardingAckEvent
  | BridgeInputForwardingAckEvent
  | BridgeBackForwardingAckEvent

export interface BridgeErrorEvent {
  type: 'error'
  code: string
  message: string
  clientCommandId?: string
}

export interface BridgeClosedEvent {
  type: 'closed'
  reason?: string
}

export type BridgeServerEvent =
  | BridgeHelloEvent
  | BridgePacketConfigurationEvent
  | BridgePacketDataEvent
  | BridgeSizeChangedEvent
  | BridgeForwardingAckEvent
  | BridgeErrorEvent
  | BridgeClosedEvent

export interface PointerCommandPayload {
  clientCommandId: string
  pointerId: number
  x: number
  y: number
  width: number
  height: number
}
