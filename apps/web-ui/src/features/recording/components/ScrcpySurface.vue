<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import {
  decodeBase64ToBytes,
  openBridgeSocket,
  sendBackCommand,
  sendInputCommand,
  sendPointerDownCommand,
  sendPointerMoveCommand,
  sendPointerUpCommand
} from '../lib/bridgeApi'
import type {
  BridgeHelloEvent,
  BridgeServerEvent,
  PointerCommandPayload,
} from '../types'
import type { ForwardingAckRequest } from '@/shared/api/recording'
import type {
  BackInteractionPayload,
  ClickInteractionPayload,
  InputInteractionPayload,
  InteractionPayload,
  SwipeInteractionPayload,
} from '@/shared/api/recording.types'

import { WebCodecsVideoDecoder } from '@yume-chan/scrcpy-decoder-webcodecs'
import { ScrcpyVideoCodecId } from '@yume-chan/scrcpy'
import type { ScrcpyMediaStreamPacket } from '@yume-chan/scrcpy'
import { BitmapVideoFrameRenderer } from '@yume-chan/scrcpy-decoder-webcodecs/esm/video/render/bitmap.js'

const props = defineProps<{
  wsUrl: string
}>()

const emit = defineEmits<{
  (e: 'interactionForwarded', payload: {
    interaction: InteractionPayload
    ack: ForwardingAckRequest
  }): void
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
const status = ref<'idle' | 'connecting' | 'ready' | 'error' | 'closed'>('idle')
const errorMessage = ref<string | null>(null)
const inputText = ref('')

const PRIMARY_POINTER_ID = 0
const CLICK_DISTANCE_THRESHOLD = 12
const MIN_SWIPE_DURATION_MS = 120

interface CanvasPoint {
  x: number
  y: number
  width: number
  height: number
}

interface ActivePointerGesture {
  clientCommandId: string
  domPointerId: number
  bridgePointerId: number
  startedAt: number
  startPoint: CanvasPoint
  lastPoint: CanvasPoint
  lastSentPoint: CanvasPoint
  pendingMovePoint: CanvasPoint | null
}

let socket: WebSocket | null = null
let hello: BridgeHelloEvent | null = null
let decoder: WebCodecsVideoDecoder | null = null
let decoderWriter: WritableStreamDefaultWriter<ScrcpyMediaStreamPacket> | null = null
let commandSeq = 0
let activePointer: ActivePointerGesture | null = null
let moveFrameRequestId: number | null = null
const pendingInteractions = new Map<string, InteractionPayload>()

const videoSizeText = computed(() => {
  const width = hello?.width ?? decoder?.width ?? 0
  const height = hello?.height ?? decoder?.height ?? 0
  if (!width || !height) {
    return 'unknown'
  }
  return `${width}x${height}`
})

function setCommandError(message: string) {
  errorMessage.value = message
}

function setError(message: string) {
  status.value = 'error'
  errorMessage.value = message
}

function ensureDecoder(codec: number) {
  if (decoder && decoderWriter) {
    return
  }
  const canvas = canvasRef.value
  if (!canvas) {
    throw new Error('canvas not ready')
  }
  if (!WebCodecsVideoDecoder.isSupported) {
    throw new Error('WebCodecs is not supported in this browser')
  }
  const renderer = new BitmapVideoFrameRenderer(canvas)
  decoder = new WebCodecsVideoDecoder({
    codec: codec as ScrcpyVideoCodecId,
    renderer
  })
  decoderWriter = decoder.writable.getWriter()
}

function handleBridgeEvent(event: BridgeServerEvent) {
  if (event.type === 'hello') {
    hello = event
    try {
      ensureDecoder(event.codec)
      status.value = 'ready'
    } catch (error) {
      setError(error instanceof Error ? error.message : String(error))
    }
    return
  }
  if (event.type === 'packet_configuration') {
    try {
      if (!hello) {
        return
      }
      ensureDecoder(hello.codec)
      const bytes = decodeBase64ToBytes(event.dataBase64)
      void decoderWriter?.write({ type: 'configuration', data: bytes })
    } catch (error) {
      setError(error instanceof Error ? error.message : String(error))
    }
    return
  }
  if (event.type === 'packet_data') {
    try {
      if (!hello) {
        return
      }
      ensureDecoder(hello.codec)
      const bytes = decodeBase64ToBytes(event.dataBase64)
      void decoderWriter?.write({
        type: 'data',
        data: bytes,
        keyframe: event.keyframe,
        pts: event.pts ? BigInt(event.pts) : undefined
      })
    } catch (error) {
      setError(error instanceof Error ? error.message : String(error))
    }
    return
  }
  if (event.type === 'error') {
    if (event.clientCommandId) {
      pendingInteractions.delete(event.clientCommandId)
      if (activePointer?.clientCommandId === event.clientCommandId) {
        abortActivePointerLocalState()
      }
      setCommandError(`[${event.code}] ${event.message}`)
      return
    }
    setError(`[${event.code}] ${event.message}`)
    return
  }
  if (event.type === 'forwarding_ack') {
    const interaction = pendingInteractions.get(event.clientCommandId)
    if (interaction) {
      pendingInteractions.delete(event.clientCommandId)
      emit('interactionForwarded', {
        interaction,
        ack: {
          kind: event.kind,
          dispatched_at: event.dispatchedAt,
          ack_at: event.ackAt,
          payload: event.payload,
          steps: event.steps.map((step) => ({
            seq: step.seq,
            step_kind: step.stepKind,
            payload: step.payload,
            dispatched_at: step.dispatchedAt
          })),
          device_result: event.deviceResult
        }
      })
    }
    return
  }
  if (event.type === 'closed') {
    status.value = 'closed'
  }
}

function connect() {
  disconnect()
  status.value = 'connecting'
  errorMessage.value = null
  socket = openBridgeSocket(props.wsUrl, {
    onEvent: handleBridgeEvent,
    onError: (message) => setError(message),
    onClosed: () => {
      status.value = 'closed'
    }
  })
}

function releaseCanvasPointerCapture(pointerId: number) {
  const canvas = canvasRef.value
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

function clearMoveFlush() {
  if (moveFrameRequestId !== null) {
    window.cancelAnimationFrame(moveFrameRequestId)
    moveFrameRequestId = null
  }
}

function disconnect() {
  cleanupActivePointer()
  socket?.close()
  socket = null
  hello = null
  void decoderWriter?.close()
  decoderWriter = null
  decoder?.dispose()
  decoder = null
  pendingInteractions.clear()
}

function nextCommandId(): string {
  commandSeq += 1
  return `cmd-${Date.now()}-${commandSeq}`
}

function resolveCanvasPoint(event: MouseEvent | PointerEvent): CanvasPoint | null {
  if (!socket || status.value !== 'ready') {
    return null
  }
  const canvas = canvasRef.value
  if (!canvas || !decoder) {
    return null
  }
  const rect = canvas.getBoundingClientRect()
  const xRatio = (event.clientX - rect.left) / rect.width
  const yRatio = (event.clientY - rect.top) / rect.height
  const videoWidth = decoder.width || hello?.width || 0
  const videoHeight = decoder.height || hello?.height || 0
  if (!videoWidth || !videoHeight) {
    setError('video size not ready')
    return null
  }
  return {
    x: Math.max(0, Math.min(videoWidth - 1, Math.round(xRatio * videoWidth))),
    y: Math.max(0, Math.min(videoHeight - 1, Math.round(yRatio * videoHeight))),
    width: videoWidth,
    height: videoHeight
  }
}

function nextPointerPayload(gesture: ActivePointerGesture, point: CanvasPoint): PointerCommandPayload {
  return {
    clientCommandId: gesture.clientCommandId,
    pointerId: gesture.bridgePointerId,
    x: point.x,
    y: point.y,
    width: point.width,
    height: point.height
  }
}

function flushPendingMoveForGesture(gesture: ActivePointerGesture) {
  if (!socket || status.value !== 'ready' || gesture.pendingMovePoint === null) {
    return
  }
  const point = gesture.pendingMovePoint
  gesture.pendingMovePoint = null
  if (point.x === gesture.lastSentPoint.x && point.y === gesture.lastSentPoint.y) {
    return
  }
  sendPointerMoveCommand(socket, nextPointerPayload(gesture, point))
  gesture.lastSentPoint = point
}

function scheduleMoveFlush() {
  if (!activePointer || moveFrameRequestId !== null) {
    return
  }
  moveFrameRequestId = window.requestAnimationFrame(() => {
    moveFrameRequestId = null
    if (activePointer) {
      flushPendingMoveForGesture(activePointer)
    }
  })
}

function classifyInteraction(
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

function cleanupActivePointer() {
  const gesture = abortActivePointerLocalState()
  if (!gesture) {
    return
  }
  if (!socket || status.value !== 'ready') {
    return
  }
  flushPendingMoveForGesture(gesture)
  sendPointerUpCommand(socket, nextPointerPayload(gesture, gesture.lastPoint))
}

function abortActivePointerLocalState(): ActivePointerGesture | null {
  const gesture = activePointer
  if (!gesture) {
    return null
  }
  clearMoveFlush()
  activePointer = null
  releaseCanvasPointerCapture(gesture.domPointerId)
  return gesture
}

function handlePointerDown(event: PointerEvent) {
  if (event.button !== 0 || activePointer) {
    return
  }
  const point = resolveCanvasPoint(event)
  if (!point || !socket) {
    return
  }
  event.preventDefault()
  canvasRef.value?.setPointerCapture(event.pointerId)
  const gesture: ActivePointerGesture = {
    clientCommandId: nextCommandId(),
    domPointerId: event.pointerId,
    bridgePointerId: PRIMARY_POINTER_ID,
    startedAt: Date.now(),
    startPoint: point,
    lastPoint: point,
    lastSentPoint: point,
    pendingMovePoint: null
  }
  activePointer = gesture
  sendPointerDownCommand(socket, nextPointerPayload(gesture, point))
}

function handlePointerMove(event: PointerEvent) {
  if (!activePointer || event.pointerId !== activePointer.domPointerId) {
    return
  }
  const point = resolveCanvasPoint(event)
  if (!point) {
    return
  }
  event.preventDefault()
  activePointer.lastPoint = point
  activePointer.pendingMovePoint = point
  scheduleMoveFlush()
}

function handlePointerUp(event: PointerEvent) {
  if (!activePointer || event.pointerId !== activePointer.domPointerId || !socket) {
    return
  }
  event.preventDefault()
  const gesture = activePointer
  const point = resolveCanvasPoint(event) ?? gesture.lastPoint
  clearMoveFlush()
  flushPendingMoveForGesture(gesture)
  activePointer = null
  releaseCanvasPointerCapture(gesture.domPointerId)
  const interaction = classifyInteraction(gesture, point)
  pendingInteractions.set(interaction.clientCommandId, interaction)
  sendPointerUpCommand(socket, nextPointerPayload(gesture, point))
}

function handlePointerCancel(event: PointerEvent) {
  if (!activePointer || event.pointerId !== activePointer.domPointerId) {
    return
  }
  event.preventDefault()
  cleanupActivePointer()
}

function handleWindowBlur() {
  cleanupActivePointer()
}

function handleBack() {
  if (!socket || status.value !== 'ready') {
    return
  }
  const payload: BackInteractionPayload = {
    kind: 'back',
    clientCommandId: nextCommandId()
  }
  pendingInteractions.set(payload.clientCommandId, payload)
  sendBackCommand(socket, payload)
}

function handleInput() {
  if (!socket || status.value !== 'ready' || !inputText.value.trim()) {
    return
  }
  const payload: InputInteractionPayload = {
    kind: 'input',
    clientCommandId: nextCommandId(),
    text: inputText.value
  }
  pendingInteractions.set(payload.clientCommandId, payload)
  sendInputCommand(socket, payload)
  inputText.value = ''
}

onMounted(() => {
  connect()
  window.addEventListener('blur', handleWindowBlur)
})

onBeforeUnmount(() => {
  window.removeEventListener('blur', handleWindowBlur)
  disconnect()
})
</script>

<template>
  <div class="scrcpy-surface">
    <div class="meta-toolbar">
      <div class="status-info">
        <span class="badge" :class="status">{{ status }}</span>
        <span>{{ videoSizeText }}</span>
        <span v-if="errorMessage" class="error-msg">{{ errorMessage }}</span>
      </div>
      <div class="actions">
        <button :disabled="status !== 'ready'" @click="handleBack">Back</button>
        <div class="input-group">
          <input
            v-model="inputText"
            :disabled="status !== 'ready'"
            type="text"
            placeholder="Input text"
            @keydown.enter.prevent="handleInput"
          >
          <button :disabled="status !== 'ready' || !inputText.trim()" @click="handleInput">Send</button>
        </div>
        <button v-if="status === 'error' || status === 'closed'" class="primary" @click="connect">Reconnect</button>
      </div>
    </div>
    <div class="canvas-container">
      <canvas
        ref="canvasRef"
        class="canvas"
        @pointerdown="handlePointerDown"
        @pointermove="handlePointerMove"
        @pointerup="handlePointerUp"
        @pointercancel="handlePointerCancel"
        @lostpointercapture="handlePointerCancel"
      ></canvas>
    </div>
  </div>
</template>

<style scoped>
.scrcpy-surface {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  background: var(--surface-default);
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--border-default);
}

.meta-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-default);
  background: var(--surface-muted);
  flex-wrap: wrap;
  gap: 12px;
}

.status-info {
  display: flex;
  align-items: center;
  gap: 12px;
  font-family: ui-monospace, SFMono-Regular, Consolas, 'Courier New', monospace;
  font-size: 12px;
  color: var(--text-secondary);
}

.badge {
  padding: 2px 8px;
  border-radius: 12px;
  background: var(--border-default);
  color: var(--text-primary);
  font-weight: 600;
  text-transform: uppercase;
  font-size: 11px;
}

.badge.ready {
  background: var(--status-success-bg);
  color: var(--status-success-text);
}

.badge.error {
  background: var(--status-error-bg);
  color: var(--status-error-text);
}

.error-msg {
  color: var(--status-error-text);
}

.actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.input-group {
  display: flex;
  gap: 4px;
}

.input-group input {
  min-width: 140px;
}

.canvas-container {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #000;
  overflow: hidden;
  position: relative;
}

.canvas {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  touch-action: none;
  user-select: none;
}
</style>
