import {
  sendPointerDownCommand,
  sendPointerMoveCommand,
  sendPointerUpCommand
} from './bridgeApi'
import type {
  ActivePointerGesture,
  CanvasPoint,
  ScrcpyPointerControllerOptions,
} from './scrcpySurfaceTypes'
import type {
  ClickInteractionPayload,
  SwipeInteractionPayload,
} from '@/shared/api/recording.types'

const PRIMARY_POINTER_ID = 0
const CLICK_DISTANCE_THRESHOLD = 12
const MIN_SWIPE_DURATION_MS = 120

export class ScrcpyPointerController {
  private activePointer: ActivePointerGesture | null = null

  private moveFrameRequestId: number | null = null

  constructor(private readonly options: ScrcpyPointerControllerOptions) {}

  abortCommand(clientCommandId: string): void {
    if (this.activePointer?.clientCommandId !== clientCommandId) {
      return
    }

    this.abortActivePointerLocalState()
  }

  cleanupActivePointer(): void {
    const gesture = this.abortActivePointerLocalState()
    const socket = this.getReadySocket()
    if (!gesture || !socket) {
      return
    }

    this.flushPendingMoveForGesture(gesture, socket)
    sendPointerUpCommand(socket, this.toPointerPayload(gesture, gesture.lastPoint))
  }

  handlePointerDown(event: PointerEvent): void {
    if (event.button !== 0 || this.activePointer) {
      return
    }

    const point = this.resolveCanvasPoint(event)
    const socket = this.getReadySocket()
    if (!point || !socket) {
      return
    }

    event.preventDefault()
    this.options.canvasRef.value?.setPointerCapture(event.pointerId)
    const gesture: ActivePointerGesture = {
      clientCommandId: this.options.nextCommandId(),
      domPointerId: event.pointerId,
      bridgePointerId: PRIMARY_POINTER_ID,
      startedAt: Date.now(),
      startPoint: point,
      lastPoint: point,
      lastSentPoint: point,
      pendingMovePoint: null
    }
    this.activePointer = gesture
    sendPointerDownCommand(socket, this.toPointerPayload(gesture, point))
  }

  handlePointerMove(event: PointerEvent): void {
    if (!this.activePointer || event.pointerId !== this.activePointer.domPointerId) {
      return
    }

    const point = this.resolveCanvasPoint(event)
    if (!point) {
      return
    }

    event.preventDefault()
    this.activePointer.lastPoint = point
    this.activePointer.pendingMovePoint = point
    this.scheduleMoveFlush()
  }

  handlePointerUp(event: PointerEvent): void {
    if (!this.activePointer || event.pointerId !== this.activePointer.domPointerId) {
      return
    }

    const socket = this.getReadySocket()
    if (!socket) {
      return
    }

    event.preventDefault()
    const gesture = this.activePointer
    const point = this.resolveCanvasPoint(event) ?? gesture.lastPoint
    this.clearMoveFlush()
    this.flushPendingMoveForGesture(gesture, socket)
    this.activePointer = null
    this.releaseCanvasPointerCapture(gesture.domPointerId)

    const interaction = this.classifyInteraction(gesture, point)
    this.options.registerPendingInteraction(interaction)
    sendPointerUpCommand(socket, this.toPointerPayload(gesture, point))
  }

  handlePointerCancel(event: PointerEvent): void {
    if (!this.activePointer || event.pointerId !== this.activePointer.domPointerId) {
      return
    }

    event.preventDefault()
    this.cleanupActivePointer()
  }

  private abortActivePointerLocalState(): ActivePointerGesture | null {
    const gesture = this.activePointer
    if (!gesture) {
      return null
    }

    this.clearMoveFlush()
    this.activePointer = null
    this.releaseCanvasPointerCapture(gesture.domPointerId)
    return gesture
  }

  private classifyInteraction(
    gesture: ActivePointerGesture,
    point: CanvasPoint
  ): ClickInteractionPayload | SwipeInteractionPayload {
    const durationMs = Math.max(0, Date.now() - gesture.startedAt)
    const deltaX = point.x - gesture.startPoint.x
    const deltaY = point.y - gesture.startPoint.y
    const distance = Math.sqrt((deltaX ** 2) + (deltaY ** 2))

    if (distance < CLICK_DISTANCE_THRESHOLD) {
      return {
        kind: 'click',
        clientCommandId: gesture.clientCommandId,
        x: point.x,
        y: point.y,
        width: point.width,
        height: point.height
      }
    }

    return {
      kind: 'swipe',
      clientCommandId: gesture.clientCommandId,
      startX: gesture.startPoint.x,
      startY: gesture.startPoint.y,
      endX: point.x,
      endY: point.y,
      width: point.width,
      height: point.height,
      durationMs: Math.max(MIN_SWIPE_DURATION_MS, durationMs)
    }
  }

  private clearMoveFlush(): void {
    if (this.moveFrameRequestId === null) {
      return
    }

    window.cancelAnimationFrame(this.moveFrameRequestId)
    this.moveFrameRequestId = null
  }

  private flushPendingMoveForGesture(gesture: ActivePointerGesture, socket: WebSocket): void {
    if (gesture.pendingMovePoint === null) {
      return
    }

    const point = gesture.pendingMovePoint
    gesture.pendingMovePoint = null
    if (point.x === gesture.lastSentPoint.x && point.y === gesture.lastSentPoint.y) {
      return
    }

    sendPointerMoveCommand(socket, this.toPointerPayload(gesture, point))
    gesture.lastSentPoint = point
  }

  private getReadySocket(): WebSocket | null {
    const session = this.options.getSessionState()
    if (!session.isReady) {
      return null
    }

    return session.socket
  }

  private releaseCanvasPointerCapture(pointerId: number): void {
    const canvas = this.options.canvasRef.value
    if (!canvas) {
      return
    }

    try {
      if (canvas.hasPointerCapture(pointerId)) {
        canvas.releasePointerCapture(pointerId)
      }
    } catch {
      // Ignore invalid release errors during teardown.
    }
  }

  private resolveCanvasPoint(event: PointerEvent): CanvasPoint | null {
    const session = this.options.getSessionState()
    if (!session.socket || !session.isReady) {
      return null
    }

    const canvas = this.options.canvasRef.value
    if (!canvas) {
      return null
    }

    if (!session.videoWidth || !session.videoHeight) {
      this.options.setError('video size not ready')
      return null
    }

    const rect = canvas.getBoundingClientRect()
    const xRatio = (event.clientX - rect.left) / rect.width
    const yRatio = (event.clientY - rect.top) / rect.height
    return {
      x: Math.max(0, Math.min(session.videoWidth - 1, Math.round(xRatio * session.videoWidth))),
      y: Math.max(0, Math.min(session.videoHeight - 1, Math.round(yRatio * session.videoHeight))),
      width: session.videoWidth,
      height: session.videoHeight
    }
  }

  private scheduleMoveFlush(): void {
    if (!this.activePointer || this.moveFrameRequestId !== null) {
      return
    }

    this.moveFrameRequestId = window.requestAnimationFrame(() => {
      this.moveFrameRequestId = null
      const socket = this.getReadySocket()
      if (this.activePointer && socket) {
        this.flushPendingMoveForGesture(this.activePointer, socket)
      }
    })
  }

  private toPointerPayload(gesture: ActivePointerGesture, point: CanvasPoint) {
    return {
      clientCommandId: gesture.clientCommandId,
      pointerId: gesture.bridgePointerId,
      x: point.x,
      y: point.y,
      width: point.width,
      height: point.height
    }
  }
}
