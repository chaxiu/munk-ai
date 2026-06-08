import 'fastify'

import type { RecordingBridgeSessionManager } from './session_manager.js'

declare module 'fastify' {
  interface FastifyInstance {
    recordingBridgeSessionManager: RecordingBridgeSessionManager
  }
}
