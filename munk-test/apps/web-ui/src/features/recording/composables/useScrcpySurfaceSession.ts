import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import type { Ref } from 'vue'

import { openBridgeSocket, sendBackCommand, sendInputCommand } from '../lib/bridgeApi'
import { ScrcpyDecoderController } from '../lib/scrcpyDecoderController'
import { mapForwardingAckEvent } from '../lib/scrcpyForwarding'
import { ScrcpyPointerController } from '../lib/scrcpyPointerController'
import type {
  ScrcpyInteractionForwardedPayload,
  ScrcpySurfaceStatus,
} from '../lib/scrcpySurfaceTypes'
import type { BridgeServerEvent } from '../types'
import type {
  BackInteractionPayload,
  InputInteractionPayload,
  InteractionPayload,
} from '@/shared/api/recording.types'

interface UseScrcpySurfaceSessionOptions {
  wsUrl: string
  onInteractionForwarded: (payload: ScrcpyInteractionForwardedPayload) => void
}

interface BridgeEventHandlerOptions {
  decoderController: ScrcpyDecoderController
  pendingInteractions: Map<string, InteractionPayload>
  pointerController: ScrcpyPointerController
  onInteractionForwarded: (payload: ScrcpyInteractionForwardedPayload) => void
  setCommandError: (message: string) => void
  setError: (message: string) => void
  setStatus: (status: ScrcpySurfaceStatus) => void
}

function toErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

function withDecoderGuard(action: () => void, setError: (message: string) => void): void {
  try {
    action()
  } catch (error) {
    setError(toErrorMessage(error))
  }
}

function createBridgeEventHandlers(options: BridgeEventHandlerOptions) {
  return {
    hello(event: Extract<BridgeServerEvent, { type: 'hello' }>) {
      withDecoderGuard(() => options.decoderController.handleHello(event), options.setError)
      options.setStatus('ready')
    },
    packet_configuration(event: Extract<BridgeServerEvent, { type: 'packet_configuration' }>) {
      withDecoderGuard(() => options.decoderController.handleConfigurationPacket(event.dataBase64), options.setError)
    },
    packet_data(event: Extract<BridgeServerEvent, { type: 'packet_data' }>) {
      withDecoderGuard(() => options.decoderController.handleDataPacket(event), options.setError)
    },
    size_changed(event: Extract<BridgeServerEvent, { type: 'size_changed' }>) {
      options.decoderController.updateSize(event.width, event.height)
    },
    forwarding_ack(event: Extract<BridgeServerEvent, { type: 'forwarding_ack' }>) {
      const interaction = options.pendingInteractions.get(event.clientCommandId)
      if (!interaction) {
        return
      }

      options.pendingInteractions.delete(event.clientCommandId)
      options.onInteractionForwarded({
        interaction,
        ack: mapForwardingAckEvent(event)
      })
    },
    error(event: Extract<BridgeServerEvent, { type: 'error' }>) {
      if (event.clientCommandId) {
        options.pendingInteractions.delete(event.clientCommandId)
        options.pointerController.abortCommand(event.clientCommandId)
        options.setCommandError(`[${event.code}] ${event.message}`)
        return
      }

      options.setError(`[${event.code}] ${event.message}`)
    },
    closed() {
      options.setStatus('closed')
    }
  }
}

function handleBridgeEvent(
  event: BridgeServerEvent,
  handlers: ReturnType<typeof createBridgeEventHandlers>
): void {
  switch (event.type) {
    case 'hello':
      handlers.hello(event)
      return
    case 'packet_configuration':
      handlers.packet_configuration(event)
      return
    case 'packet_data':
      handlers.packet_data(event)
      return
    case 'size_changed':
      handlers.size_changed(event)
      return
    case 'forwarding_ack':
      handlers.forwarding_ack(event)
      return
    case 'error':
      handlers.error(event)
      return
    case 'closed':
      handlers.closed()
  }
}

function createScrcpySurfaceRuntime(options: {
  canvasRef: Ref<HTMLCanvasElement | null>
  pendingInteractions: Map<string, InteractionPayload>
  status: Ref<ScrcpySurfaceStatus>
  setCommandError: (message: string) => void
  setError: (message: string) => void
  nextCommandId: () => string
  onInteractionForwarded: (payload: ScrcpyInteractionForwardedPayload) => void
}) {
  const runtime = {
    bridgeEventHandlers: null as ReturnType<typeof createBridgeEventHandlers> | null,
    decoderController: new ScrcpyDecoderController(options.canvasRef),
    pointerController: null as ScrcpyPointerController | null,
    socket: null as WebSocket | null
  }

  runtime.pointerController = new ScrcpyPointerController({
    canvasRef: options.canvasRef,
    getSessionState: () => {
      const videoSize = runtime.decoderController.getVideoSize()
      return {
        socket: runtime.socket,
        isReady: options.status.value === 'ready',
        videoWidth: videoSize.width,
        videoHeight: videoSize.height
      }
    },
    nextCommandId: options.nextCommandId,
    setError: options.setError,
    registerPendingInteraction: (interaction) => {
      options.pendingInteractions.set(interaction.clientCommandId, interaction)
    }
  })

  runtime.bridgeEventHandlers = createBridgeEventHandlers({
    decoderController: runtime.decoderController,
    pendingInteractions: options.pendingInteractions,
    pointerController: runtime.pointerController,
    onInteractionForwarded: options.onInteractionForwarded,
    setCommandError: options.setCommandError,
    setError: options.setError,
    setStatus: (nextStatus) => {
      options.status.value = nextStatus
    }
  })

  return runtime as {
    bridgeEventHandlers: ReturnType<typeof createBridgeEventHandlers>
    decoderController: ScrcpyDecoderController
    pointerController: ScrcpyPointerController
    socket: WebSocket | null
  }
}

export function useScrcpySurfaceSession(options: UseScrcpySurfaceSessionOptions) {
  const canvasRef = ref<HTMLCanvasElement | null>(null)
  const status = ref<ScrcpySurfaceStatus>('idle')
  const errorMessage = ref<string | null>(null)
  const inputText = ref('')

  let socket: WebSocket | null = null
  let commandSeq = 0
  const pendingInteractions = new Map<string, InteractionPayload>()

  const setCommandError = (message: string) => {
    errorMessage.value = message
  }

  const setError = (message: string) => {
    status.value = 'error'
    errorMessage.value = message
  }

  const nextCommandId = () => {
    commandSeq += 1
    return `cmd-${Date.now()}-${commandSeq}`
  }

  const runtime = createScrcpySurfaceRuntime({
    canvasRef,
    pendingInteractions,
    status,
    setCommandError,
    setError,
    nextCommandId,
    onInteractionForwarded: options.onInteractionForwarded
  })

  const videoSizeText = computed(() => {
    const { width, height } = runtime.decoderController.getVideoSize()
    return width && height ? `${width}x${height}` : 'unknown'
  })

  const handleWindowBlur = () => {
    runtime.pointerController.cleanupActivePointer()
  }

  const handlePointerCancel = runtime.pointerController.handlePointerCancel.bind(runtime.pointerController)
  const handlePointerDown = runtime.pointerController.handlePointerDown.bind(runtime.pointerController)
  const handlePointerMove = runtime.pointerController.handlePointerMove.bind(runtime.pointerController)
  const handlePointerUp = runtime.pointerController.handlePointerUp.bind(runtime.pointerController)

  const disconnect = () => {
    runtime.pointerController.cleanupActivePointer()
    socket?.close()
    socket = null
    runtime.socket = null
    runtime.decoderController.dispose()
    pendingInteractions.clear()
  }

  const connect = () => {
    disconnect()
    status.value = 'connecting'
    errorMessage.value = null

    const currentSocket = openBridgeSocket(options.wsUrl, {
      onEvent: (event) => {
        if (socket !== currentSocket) {
          return
        }
        handleBridgeEvent(event, runtime.bridgeEventHandlers)
      },
      onError: (message) => {
        if (socket === currentSocket) {
          setError(message)
        }
      },
      onClosed: () => {
        if (socket === currentSocket) {
          status.value = 'closed'
        }
      }
    })
    socket = currentSocket
    runtime.socket = currentSocket
  }

  const handleBack = () => {
    if (!socket || status.value !== 'ready') {
      return
    }

    const payload: BackInteractionPayload = { kind: 'back', clientCommandId: nextCommandId() }
    pendingInteractions.set(payload.clientCommandId, payload)
    sendBackCommand(socket, payload)
  }

  const handleInput = () => {
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

  return {
    canvasRef,
    connect,
    errorMessage,
    handleBack,
    handleInput,
    handlePointerCancel,
    handlePointerDown,
    handlePointerMove,
    handlePointerUp,
    inputText,
    status,
    videoSizeText
  }
}
