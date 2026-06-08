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

export interface BridgeForwardingStep {
  seq: number
  stepKind: 'pointer_down' | 'pointer_move' | 'pointer_up' | 'key_press' | 'key_down' | 'key_up' | 'text_inject'
  payload: Record<string, unknown>
  dispatchedAt: string
}

export interface BridgeForwardingAckEvent {
  type: 'forwarding_ack'
  clientCommandId: string
  kind: 'pointer' | 'input' | 'back'
  ackAt: string
  dispatchedAt?: string
  payload: Record<string, unknown>
  steps: BridgeForwardingStep[]
  deviceResult: Record<string, unknown>
}

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
