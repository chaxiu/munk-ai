import type {
  BridgeServerEvent,
  PointerCommandPayload
} from '../types'
import type {
  BackInteractionPayload,
  InputInteractionPayload,
} from '@/shared/api/recording.types'

export function openBridgeSocket (
  wsUrl: string,
  handlers: {
    onEvent: (event: BridgeServerEvent) => void
    onError: (message: string) => void
    onClosed: () => void
  }
): WebSocket {
  const socket = new WebSocket(wsUrl)
  socket.addEventListener('message', (evt) => {
    if (typeof evt.data !== 'string') {
      handlers.onError('bridge websocket message must be text')
      return
    }
    try {
      const event = JSON.parse(evt.data) as BridgeServerEvent
      handlers.onEvent(event)
    } catch (error) {
      handlers.onError(error instanceof Error ? error.message : String(error))
    }
  })
  socket.addEventListener('close', () => {
    handlers.onClosed()
  })
  socket.addEventListener('error', () => {
    handlers.onError('bridge websocket error')
  })
  return socket
}

export function sendPointerDownCommand (socket: WebSocket, payload: PointerCommandPayload): void {
  socket.send(JSON.stringify({
    type: 'pointer_down',
    clientCommandId: payload.clientCommandId,
    pointerId: payload.pointerId,
    x: payload.x,
    y: payload.y,
    width: payload.width,
    height: payload.height
  }))
}

export function sendPointerMoveCommand (socket: WebSocket, payload: PointerCommandPayload): void {
  socket.send(JSON.stringify({
    type: 'pointer_move',
    clientCommandId: payload.clientCommandId,
    pointerId: payload.pointerId,
    x: payload.x,
    y: payload.y,
    width: payload.width,
    height: payload.height
  }))
}

export function sendPointerUpCommand (socket: WebSocket, payload: PointerCommandPayload): void {
  socket.send(JSON.stringify({
    type: 'pointer_up',
    clientCommandId: payload.clientCommandId,
    pointerId: payload.pointerId,
    x: payload.x,
    y: payload.y,
    width: payload.width,
    height: payload.height
  }))
}

export function sendInputCommand (socket: WebSocket, payload: InputInteractionPayload): void {
  socket.send(JSON.stringify({
    type: 'input',
    clientCommandId: payload.clientCommandId,
    text: payload.text,
    submit: payload.submit === true
  }))
}

export function sendBackCommand (socket: WebSocket, payload: BackInteractionPayload): void {
  socket.send(JSON.stringify({
    type: 'back',
    clientCommandId: payload.clientCommandId
  }))
}

export function decodeBase64ToBytes (value: string): Uint8Array {
  const binary = atob(value)
  const out = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i += 1) {
    out[i] = binary.charCodeAt(i)
  }
  return out
}
