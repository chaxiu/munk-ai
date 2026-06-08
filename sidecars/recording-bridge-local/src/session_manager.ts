import type WebSocket from 'ws'

import type { BridgeClientCommand, CreateBridgeSessionRequest } from './protocol.js'
import { ScrcpySession } from './scrcpy_session.js'

export class RecordingBridgeSessionManager {
  private readonly sessions = new Map<string, ScrcpySession>()

  async createSession ({ recording_id: recordingId, device_ref: deviceRef }: CreateBridgeSessionRequest): Promise<ScrcpySession> {
    const existing = this.sessions.get(recordingId)
    if (existing) {
      return existing
    }
    const session = new ScrcpySession({
      recordingId,
      deviceRef
    })
    this.sessions.set(recordingId, session)
    return session
  }

  getSession (recordingId: string): ScrcpySession {
    const session = this.sessions.get(recordingId)
    if (!session) {
      throw new Error(`recording session '${recordingId}' was not found`)
    }
    return session
  }

  hasSession (recordingId: string): boolean {
    return this.sessions.has(recordingId)
  }

  async startSession (recordingId: string): Promise<ScrcpySession> {
    const session = this.getSession(recordingId)
    await session.start()
    return session
  }

  async dispatchCommand (recordingId: string, command: BridgeClientCommand) {
    const session = this.getSession(recordingId)
    if (command.type === 'pointer_down') {
      return session.pointerDown(command)
    }
    if (command.type === 'pointer_move') {
      return session.pointerMove(command)
    }
    if (command.type === 'pointer_up') {
      return session.pointerUp(command)
    }
    if (command.type === 'input') {
      return session.input(command)
    }
    if (command.type === 'back') {
      return session.back(command)
    }
    throw new Error('unsupported bridge command type')
  }

  attachSocket (recordingId: string, socket: WebSocket): ScrcpySession {
    const session = this.getSession(recordingId)
    session.addSocketClient(socket)
    return session
  }

  detachSocket (recordingId: string, socket: WebSocket): void {
    const session = this.sessions.get(recordingId)
    session?.removeSocketClient(socket)
  }

  async deleteSession (recordingId: string): Promise<void> {
    const session = this.sessions.get(recordingId)
    if (!session) {
      return
    }
    this.sessions.delete(recordingId)
    await session.close()
  }

  async closeAll (): Promise<void> {
    const recordingIds = [...this.sessions.keys()]
    await Promise.all(recordingIds.map(async (recordingId) => this.deleteSession(recordingId)))
  }
}
