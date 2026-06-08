import { createReadStream } from 'node:fs'
import fs from 'node:fs/promises'
import { Readable } from 'node:stream'

import { AdbServerClient } from '@yume-chan/adb'
import { AdbScrcpyClient, AdbScrcpyOptionsLatest } from '@yume-chan/adb-scrcpy'
import { AdbServerNodeTcpConnector } from '@yume-chan/adb-server-node-tcp'
import {
  AndroidKeyCode,
  AndroidKeyEventAction,
  AndroidKeyEventMeta,
  AndroidMotionEventAction,
  AndroidMotionEventButton
} from '@yume-chan/scrcpy'
import type { ScrcpyMediaStreamPacket, ScrcpyVideoStreamMetadata } from '@yume-chan/scrcpy'
import type WebSocket from 'ws'

import {
  DEFAULT_ADB_SERVER_HOST,
  DEFAULT_ADB_SERVER_PORT,
  DEFAULT_MAX_FPS,
  DEFAULT_MAX_SIZE,
  DEFAULT_SCRCPY_SERVER_DEVICE_PATH,
  DEFAULT_SCRCPY_SERVER_VERSION,
  DEFAULT_VIDEO_BIT_RATE,
  resolveScrcpyServerBinaryPath
} from './config.js'
import type {
  BridgeClosedEvent,
  BridgeErrorEvent,
  BridgeForwardingAckEvent,
  BridgeForwardingStep,
  BridgeHelloEvent,
  BridgePacketConfigurationEvent,
  BridgePacketDataEvent,
  BridgePointerDownCommand,
  BridgePointerMoveCommand,
  BridgePointerUpCommand,
  BridgeServerEvent,
  BridgeSizeChangedEvent,
  BridgeBackCommand,
  BridgeInputCommand
} from './protocol.js'
import { toBase64 } from './protocol.js'

export interface ScrcpySessionInit {
  recordingId: string
  deviceRef?: string
}

interface ActivePointerTransaction {
  clientCommandId: string
  pointerId: number
  width: number
  height: number
  startX: number
  startY: number
  lastX: number
  lastY: number
  steps: BridgeForwardingStep[]
}

export class RecordingBridgeSessionError extends Error {
  code: string

  constructor (code: string, message: string) {
    super(message)
    this.name = 'RecordingBridgeSessionError'
    this.code = code
  }
}

export class ScrcpySession {
  readonly recordingId: string
  readonly deviceRef?: string

  private adbClient: AdbServerClient | null = null
  private adb: Awaited<ReturnType<AdbServerClient['createAdb']>> | null = null
  private client: AdbScrcpyClient<AdbScrcpyOptionsLatest<true>> | null = null
  private started = false
  private videoMetadata: ScrcpyVideoStreamMetadata | null = null
  private socketClients = new Set<WebSocket>()
  private videoPump: Promise<void> | null = null
  private activePointer: ActivePointerTransaction | null = null

  constructor ({ recordingId, deviceRef }: ScrcpySessionInit) {
    this.recordingId = recordingId
    this.deviceRef = deviceRef
  }

  async start (): Promise<void> {
    if (this.started) {
      return
    }
    const serverBinaryPath = resolveScrcpyServerBinaryPath()
    await ensureServerBinary(serverBinaryPath)

    this.adbClient = new AdbServerClient(
      new AdbServerNodeTcpConnector({
        host: process.env.MUNK_ADB_SERVER_HOST ?? DEFAULT_ADB_SERVER_HOST,
        port: Number(process.env.MUNK_ADB_SERVER_PORT ?? DEFAULT_ADB_SERVER_PORT)
      })
    )
    this.adb = await this.adbClient.createAdb(this.deviceRef ? { serial: this.deviceRef } : undefined)

    const binaryStream = Readable.toWeb(createReadStream(serverBinaryPath))
    await AdbScrcpyClient.pushServer(
      this.adb,
      binaryStream as never,
      DEFAULT_SCRCPY_SERVER_DEVICE_PATH
    )

    const options = new AdbScrcpyOptionsLatest({
      video: true,
      audio: false,
      control: true,
      clipboardAutosync: false,
      sendDeviceMeta: true,
      sendCodecMeta: true,
      sendFrameMeta: true,
      powerOn: true,
      tunnelForward: false,
      videoBitRate: DEFAULT_VIDEO_BIT_RATE,
      maxSize: DEFAULT_MAX_SIZE,
      maxFps: DEFAULT_MAX_FPS,
      logLevel: 'info'
    })

    this.client = await AdbScrcpyClient.start(
      this.adb,
      DEFAULT_SCRCPY_SERVER_DEVICE_PATH,
      options
    )

    const videoStream = await this.client.videoStream
    this.videoMetadata = videoStream.metadata
    videoStream.sizeChanged(({ width, height }) => {
      this.videoMetadata = {
        ...this.videoMetadata,
        width,
        height
      }
      this.broadcast({
        type: 'size_changed',
        width,
        height
      })
    })

    void this.client.output.pipeTo(new WritableStream<string>({
      write () {}
    }) as never)
    this.videoPump = this.pipeVideo(videoStream.stream as never)
    this.started = true
  }

  metadata (): ScrcpyVideoStreamMetadata {
    if (!this.videoMetadata) {
      throw new RecordingBridgeSessionError('bridge_not_started', 'scrcpy session has not started yet')
    }
    return this.videoMetadata
  }

  helloEvent (): BridgeHelloEvent {
    const metadata = this.metadata()
    return {
      type: 'hello',
      recordingId: this.recordingId,
      codec: metadata.codec,
      deviceName: metadata.deviceName,
      width: metadata.width,
      height: metadata.height
    }
  }

  addSocketClient (socket: WebSocket): void {
    this.socketClients.add(socket)
  }

  removeSocketClient (socket: WebSocket): void {
    this.socketClients.delete(socket)
  }

  async pointerDown (command: BridgePointerDownCommand): Promise<null> {
    const controller = this.requireTouchController()
    if (this.activePointer) {
      throw new RecordingBridgeSessionError(
        'pointer_transaction_already_active',
        `pointer transaction '${this.activePointer.clientCommandId}' is still active`
      )
    }
    const transaction: ActivePointerTransaction = {
      clientCommandId: command.clientCommandId,
      pointerId: command.pointerId,
      width: command.width,
      height: command.height,
      startX: command.x,
      startY: command.y,
      lastX: command.x,
      lastY: command.y,
      steps: [
        this.buildStep(1, 'pointer_down', {
          pointer_id: command.pointerId,
          x: command.x,
          y: command.y
        })
      ]
    }
    this.activePointer = transaction
    try {
      await controller.injectTouch({
        action: AndroidMotionEventAction.Down,
        pointerId: BigInt(command.pointerId),
        pointerX: command.x,
        pointerY: command.y,
        videoWidth: command.width,
        videoHeight: command.height,
        pressure: 1,
        actionButton: AndroidMotionEventButton.Primary,
        buttons: AndroidMotionEventButton.Primary
      })
    } catch (error) {
      this.activePointer = null
      throw error
    }
    return null
  }

  async pointerMove (command: BridgePointerMoveCommand): Promise<null> {
    const controller = this.requireTouchController()
    const transaction = this.requireActivePointer(command.clientCommandId, command.pointerId)
    transaction.lastX = command.x
    transaction.lastY = command.y
    transaction.width = command.width
    transaction.height = command.height
    transaction.steps.push(this.buildStep(transaction.steps.length + 1, 'pointer_move', {
      pointer_id: command.pointerId,
      x: command.x,
      y: command.y
    }))
    await controller.injectTouch({
      action: AndroidMotionEventAction.Move,
      pointerId: BigInt(command.pointerId),
      pointerX: command.x,
      pointerY: command.y,
      videoWidth: command.width,
      videoHeight: command.height,
      pressure: 1,
      actionButton: AndroidMotionEventButton.Primary,
      buttons: AndroidMotionEventButton.Primary
    })
    return null
  }

  async pointerUp (command: BridgePointerUpCommand): Promise<BridgeForwardingAckEvent> {
    const controller = this.requireTouchController()
    const transaction = this.requireActivePointer(command.clientCommandId, command.pointerId)
    transaction.lastX = command.x
    transaction.lastY = command.y
    transaction.width = command.width
    transaction.height = command.height
    transaction.steps.push(this.buildStep(transaction.steps.length + 1, 'pointer_up', {
      pointer_id: command.pointerId,
      x: command.x,
      y: command.y
    }))
    try {
      await controller.injectTouch({
        action: AndroidMotionEventAction.Up,
        pointerId: BigInt(command.pointerId),
        pointerX: command.x,
        pointerY: command.y,
        videoWidth: command.width,
        videoHeight: command.height,
        pressure: 0,
        actionButton: AndroidMotionEventButton.Primary,
        buttons: 0
      })
      return this.buildAck(command.clientCommandId, 'pointer', {
        pointer_id: command.pointerId,
        start_x: transaction.startX,
        start_y: transaction.startY,
        end_x: command.x,
        end_y: command.y,
        width: command.width,
        height: command.height
      }, [...transaction.steps])
    } finally {
      this.activePointer = null
    }
  }

  async input (command: BridgeInputCommand): Promise<BridgeForwardingAckEvent> {
    const controller = this.client?.controller as any
    if (!controller) {
      throw new RecordingBridgeSessionError('bridge_control_unavailable', 'scrcpy controller is unavailable')
    }
    if (typeof controller.injectText !== 'function') {
      throw new RecordingBridgeSessionError('bridge_text_unavailable', 'scrcpy controller does not support text injection')
    }
    const steps: BridgeForwardingStep[] = [
      this.buildStep(1, 'text_inject', { text: command.text, submit: command.submit === true })
    ]
    await controller.injectText(command.text)
    if (command.submit === true && typeof controller.injectKeyCode === 'function') {
      steps.push(this.buildStep(2, 'key_press', { key: 'enter' }))
      await controller.injectKeyCode({
        action: AndroidKeyEventAction.Down,
        keyCode: AndroidKeyCode.Enter,
        repeat: 0,
        metaState: AndroidKeyEventMeta.None
      })
      await controller.injectKeyCode({
        action: AndroidKeyEventAction.Up,
        keyCode: AndroidKeyCode.Enter,
        repeat: 0,
        metaState: AndroidKeyEventMeta.None
      })
    }
    return this.buildAck(command.clientCommandId, 'input', {
      text: command.text,
      submit: command.submit === true
    }, steps)
  }

  async back (command: BridgeBackCommand): Promise<BridgeForwardingAckEvent> {
    const controller = this.client?.controller as any
    if (!controller) {
      throw new RecordingBridgeSessionError('bridge_control_unavailable', 'scrcpy controller is unavailable')
    }
    const steps: BridgeForwardingStep[] = [
      this.buildStep(1, 'key_down', { key: 'back' }),
      this.buildStep(2, 'key_up', { key: 'back' })
    ]
    if (typeof controller.injectKeyCode !== 'function') {
      throw new RecordingBridgeSessionError('bridge_key_unavailable', 'scrcpy controller does not support key injection')
    }
    await controller.injectKeyCode({
      action: AndroidKeyEventAction.Down,
      keyCode: AndroidKeyCode.AndroidBack,
      repeat: 0,
      metaState: AndroidKeyEventMeta.None
    })
    await controller.injectKeyCode({
      action: AndroidKeyEventAction.Up,
      keyCode: AndroidKeyCode.AndroidBack,
      repeat: 0,
      metaState: AndroidKeyEventMeta.None
    })
    return this.buildAck(command.clientCommandId, 'back', {}, steps)
  }

  async close (): Promise<void> {
    this.broadcast({ type: 'closed', reason: 'session_closed' })
    for (const socket of this.socketClients) {
      socket.close()
    }
    this.socketClients.clear()
    await this.releaseActivePointer()
    if (this.client) {
      await this.client.close()
      this.client = null
    }
    if (this.adb) {
      await this.adb.close()
      this.adb = null
    }
    this.adbClient = null
    this.started = false
  }

  private async pipeVideo (stream: ReadableStream<ScrcpyMediaStreamPacket>): Promise<void> {
    const reader = stream.getReader()
    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) {
          break
        }
        if (value.type === 'configuration') {
          const event: BridgePacketConfigurationEvent = {
            type: 'packet_configuration',
            dataBase64: toBase64(value.data)
          }
          this.broadcast(event)
          continue
        }
        const event: BridgePacketDataEvent = {
          type: 'packet_data',
          dataBase64: toBase64(value.data),
          keyframe: value.keyframe,
          pts: value.pts?.toString()
        }
        this.broadcast(event)
      }
    } catch (error) {
      const event: BridgeErrorEvent = {
        type: 'error',
        code: 'video_stream_failed',
        message: error instanceof Error ? error.message : String(error)
      }
      this.broadcast(event)
    } finally {
      reader.releaseLock()
    }
  }

  private broadcast (event: BridgeServerEvent): void {
    const payload = JSON.stringify(event)
    for (const socket of this.socketClients) {
      if (socket.readyState === socket.OPEN) {
        socket.send(payload)
      }
    }
  }

  private buildStep (
    seq: number,
    stepKind: BridgeForwardingStep['stepKind'],
    payload: Record<string, unknown>
  ): BridgeForwardingStep {
    return {
      seq,
      stepKind,
      payload,
      dispatchedAt: new Date().toISOString()
    }
  }

  private buildAck (
    clientCommandId: string,
    kind: BridgeForwardingAckEvent['kind'],
    payload: Record<string, unknown>,
    steps: BridgeForwardingStep[]
  ): BridgeForwardingAckEvent {
    const ack: BridgeForwardingAckEvent = {
      type: 'forwarding_ack',
      clientCommandId,
      kind,
      ackAt: new Date().toISOString(),
      payload,
      steps,
      deviceResult: { ok: true }
    }
    this.broadcast(ack)
    return ack
  }

  private requireTouchController (): NonNullable<AdbScrcpyClient<AdbScrcpyOptionsLatest<true>>['controller']> {
    if (!this.client?.controller) {
      throw new RecordingBridgeSessionError('bridge_control_unavailable', 'scrcpy controller is unavailable')
    }
    return this.client.controller
  }

  private requireActivePointer (clientCommandId: string, pointerId: number): ActivePointerTransaction {
    const transaction = this.activePointer
    if (!transaction) {
      throw new RecordingBridgeSessionError(
        'pointer_transaction_not_found',
        `pointer transaction '${clientCommandId}' was not found`
      )
    }
    if (transaction.clientCommandId !== clientCommandId || transaction.pointerId !== pointerId) {
      throw new RecordingBridgeSessionError(
        'pointer_transaction_mismatch',
        `pointer transaction '${clientCommandId}' does not match the active pointer transaction`
      )
    }
    return transaction
  }

  private async releaseActivePointer (): Promise<void> {
    const transaction = this.activePointer
    const controller = this.client?.controller
    if (!transaction || !controller) {
      this.activePointer = null
      return
    }
    try {
      await controller.injectTouch({
        action: AndroidMotionEventAction.Up,
        pointerId: BigInt(transaction.pointerId),
        pointerX: transaction.lastX,
        pointerY: transaction.lastY,
        videoWidth: transaction.width,
        videoHeight: transaction.height,
        pressure: 0,
        actionButton: AndroidMotionEventButton.Primary,
        buttons: 0
      })
    } catch {
      // Best-effort cleanup during shutdown; the session is closing either way.
    } finally {
      this.activePointer = null
    }
  }
}

async function ensureServerBinary (filePath: string): Promise<void> {
  try {
    await fs.access(filePath)
  } catch {
    throw new RecordingBridgeSessionError(
      'scrcpy_server_binary_missing',
      `scrcpy server binary missing: ${filePath}. ` +
        'Run `pnpm --dir recording-bridge-local exec fetch-scrcpy-server 3.3.3` or set MUNK_SCRCPY_SERVER_BINARY.'
    )
  }
}
