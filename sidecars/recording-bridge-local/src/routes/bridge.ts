import { type FastifyPluginAsync, type FastifyReply } from 'fastify'

import type { CreateBridgeSessionRequest } from '../protocol.js'
import { parseBridgeClientCommand, readBridgeClientFrame } from '../protocol.js'
import { RecordingBridgeSessionError } from '../scrcpy_session.js'
import type { RecordingBridgeSessionManager } from '../session_manager.js'

const bridgeRoutes: FastifyPluginAsync = async (fastify): Promise<void> => {
  const sessionManager = fastify as typeof fastify & {
    recordingBridgeSessionManager: RecordingBridgeSessionManager
  }

  fastify.get('/healthz', async function () {
    return { status: 'ok' }
  })

  fastify.post<{ Body: CreateBridgeSessionRequest }>('/sessions', async function (request, reply) {
    const body = request.body
    if (!body?.recording_id) {
      return reply.code(400).send({
        ok: false,
        error: {
          code: 'invalid_request',
          message: 'recording_id is required'
        }
      })
    }
    const session = await sessionManager.recordingBridgeSessionManager.createSession(body)
    return {
      ok: true,
      data: {
        recording_id: session.recordingId,
        device_ref: session.deviceRef ?? null
      }
    }
  })

  fastify.post<{ Params: { recording_id: string } }>('/sessions/:recording_id/start', async function (request, reply) {
    try {
      const session = await sessionManager.recordingBridgeSessionManager.startSession(request.params.recording_id)
      return {
        ok: true,
        data: {
          recording_id: session.recordingId,
          hello: session.helloEvent()
        }
      }
    } catch (error) {
      return sendBridgeError(reply, error)
    }
  })

  fastify.delete<{ Params: { recording_id: string } }>('/sessions/:recording_id', async function (request, reply) {
    await sessionManager.recordingBridgeSessionManager.deleteSession(request.params.recording_id)
    return reply.code(204).send()
  })

  fastify.get<{ Params: { recording_id: string } }>(
    '/sessions/:recording_id/stream',
    { websocket: true },
    async function (socket, request) {
      const recordingId = request.params.recording_id
      try {
        const session = sessionManager.recordingBridgeSessionManager.attachSocket(recordingId, socket)
        socket.send(JSON.stringify(session.helloEvent()))
        socket.on('message', async (raw: unknown, isBinary: boolean) => {
          const payload = readBridgeClientFrame(raw, isBinary)
          if (payload === null) {
            socket.send(JSON.stringify({
              type: 'error',
              code: 'invalid_frame',
              message: 'only text websocket frames are supported'
            }))
            return
          }
          try {
            const command = parseBridgeClientCommand(payload)
            try {
              await sessionManager.recordingBridgeSessionManager.dispatchCommand(
                recordingId,
                command
              )
            } catch (error) {
              socket.send(JSON.stringify({
                type: 'error',
                code: 'command_failed',
                clientCommandId: command.clientCommandId,
                message: error instanceof Error ? error.message : String(error)
              }))
            }
          } catch (error) {
            socket.send(JSON.stringify({
              type: 'error',
              code: 'command_failed',
              message: error instanceof Error ? error.message : String(error)
            }))
          }
        })
        socket.on('close', () => {
          sessionManager.recordingBridgeSessionManager.detachSocket(recordingId, socket)
        })
      } catch (error) {
        socket.send(JSON.stringify({
          type: 'error',
          code: 'session_not_found',
          message: error instanceof Error ? error.message : String(error)
        }))
        socket.close()
      }
    }
  )
}

function sendBridgeError (reply: FastifyReply, error: unknown) {
  if (error instanceof RecordingBridgeSessionError) {
    return reply.code(503).send({
      ok: false,
      error: {
        code: error.code,
        message: error.message
      }
    })
  }
  return reply.code(500).send({
    ok: false,
    error: {
      code: 'bridge_start_failed',
      message: error instanceof Error ? error.message : String(error)
    }
  })
}

export default bridgeRoutes
