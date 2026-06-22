import type { Ref } from 'vue'

import type { ForwardingAckRequest } from '@/shared/api/recording'
import type { InteractionPayload } from '@/shared/api/recording.types'

export type ScrcpySurfaceStatus = 'idle' | 'connecting' | 'ready' | 'error' | 'closed'

export interface CanvasPoint {
  x: number
  y: number
  width: number
  height: number
}

export interface ActivePointerGesture {
  clientCommandId: string
  domPointerId: number
  bridgePointerId: number
  startedAt: number
  startPoint: CanvasPoint
  lastPoint: CanvasPoint
  lastSentPoint: CanvasPoint
  pendingMovePoint: CanvasPoint | null
}

export interface ScrcpyInteractionForwardedPayload {
  interaction: InteractionPayload
  ack: ForwardingAckRequest
}

export interface ScrcpySessionState {
  socket: WebSocket | null
  isReady: boolean
  videoWidth: number
  videoHeight: number
}

export interface ScrcpyPointerControllerOptions {
  canvasRef: Ref<HTMLCanvasElement | null>
  getSessionState: () => ScrcpySessionState
  nextCommandId: () => string
  setError: (message: string) => void
  registerPendingInteraction: (interaction: InteractionPayload) => void
}
