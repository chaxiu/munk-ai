export type BridgeServerEvent =
  | BridgeHelloEvent
  | BridgePacketConfigurationEvent
  | BridgePacketDataEvent
  | BridgeSizeChangedEvent
  | BridgeForwardingAckEvent
  | BridgeErrorEvent
  | BridgeClosedEvent

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

export type BridgeForwardingKind = 'pointer' | 'input' | 'back'
export type BridgeForwardingStepKind =
  | 'pointer_down'
  | 'pointer_move'
  | 'pointer_up'
  | 'key_press'
  | 'key_down'
  | 'key_up'
  | 'text_inject'

export interface BridgeForwardingStep {
  seq: number
  stepKind: BridgeForwardingStepKind
  payload: Record<string, unknown>
  dispatchedAt: string
}

export interface BridgeForwardingAckEvent {
  type: 'forwarding_ack'
  clientCommandId: string
  kind: BridgeForwardingKind
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

export type BridgeClientCommand =
  | BridgePointerDownCommand
  | BridgePointerMoveCommand
  | BridgePointerUpCommand
  | BridgeInputCommand
  | BridgeBackCommand

export interface BridgePointerDownCommand {
  type: 'pointer_down'
  clientCommandId: string
  pointerId: number
  x: number
  y: number
  width: number
  height: number
}

export interface BridgePointerMoveCommand {
  type: 'pointer_move'
  clientCommandId: string
  pointerId: number
  x: number
  y: number
  width: number
  height: number
}

export interface BridgePointerUpCommand {
  type: 'pointer_up'
  clientCommandId: string
  pointerId: number
  x: number
  y: number
  width: number
  height: number
}

export interface BridgeInputCommand {
  type: 'input'
  clientCommandId: string
  text: string
  submit?: boolean
}

export interface BridgeBackCommand {
  type: 'back'
  clientCommandId: string
}

export interface CreateBridgeSessionRequest {
  recording_id: string
  device_ref?: string
}

export function readBridgeClientFrame (raw: unknown, isBinary: boolean): string | null {
  if (isBinary) {
    return null
  }
  if (typeof raw === 'string') {
    return raw
  }
  if (raw instanceof ArrayBuffer) {
    return Buffer.from(raw).toString('utf8')
  }
  if (Buffer.isBuffer(raw)) {
    return raw.toString('utf8')
  }
  if (Array.isArray(raw)) {
    return Buffer.concat(raw.map((item) => Buffer.isBuffer(item) ? item : Buffer.from(item))).toString('utf8')
  }
  return null
}

export function toBase64 (data: Uint8Array): string {
  return Buffer.from(data).toString('base64')
}

export function parseBridgeClientCommand (payload: string): BridgeClientCommand {
  const value = JSON.parse(payload) as {
    type?: unknown
    clientCommandId?: unknown
    pointerId?: unknown
    x?: unknown
    y?: unknown
    width?: unknown
    height?: unknown
    text?: unknown
    submit?: unknown
  }
  const commandType = value.type
  if (commandType === 'pointer_down' || commandType === 'pointer_move' || commandType === 'pointer_up') {
    if (
      typeof value.clientCommandId !== 'string' ||
      typeof value.pointerId !== 'number' ||
      typeof value.x !== 'number' ||
      typeof value.y !== 'number' ||
      typeof value.width !== 'number' ||
      typeof value.height !== 'number'
    ) {
      throw new Error(
        `${value.type} command requires clientCommandId, pointerId and numeric x/y/width/height`
      )
    }
    return {
      type: commandType,
      clientCommandId: value.clientCommandId,
      pointerId: value.pointerId,
      x: value.x,
      y: value.y,
      width: value.width,
      height: value.height
    }
  }
  if (commandType === 'input') {
    if (typeof value.clientCommandId !== 'string' || typeof value.text !== 'string') {
      throw new Error('input command requires clientCommandId and text')
    }
    return {
      type: 'input',
      clientCommandId: value.clientCommandId,
      text: value.text,
      submit: value.submit === true
    }
  }
  if (commandType === 'back') {
    if (typeof value.clientCommandId !== 'string') {
      throw new Error('back command requires clientCommandId')
    }
    return {
      type: 'back',
      clientCommandId: value.clientCommandId
    }
  }
  throw new Error(`unsupported bridge command type: ${String(commandType)}`)
}
