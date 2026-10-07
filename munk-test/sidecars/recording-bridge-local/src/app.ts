import * as path from 'node:path'
import AutoLoad, { type AutoloadPluginOptions } from '@fastify/autoload'
import cors from '@fastify/cors'
import websocket from '@fastify/websocket'
import { type FastifyPluginAsync } from 'fastify'
import { fileURLToPath } from 'node:url'

import { RecordingBridgeSessionManager } from './session_manager.js'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

export type AppOptions = {
  // Place your custom options for app below here.
} & Partial<AutoloadPluginOptions>

// Pass --options via CLI arguments in command to enable these options.
const options: AppOptions = {
}

const app: FastifyPluginAsync<AppOptions> = async (
  fastify,
  opts
): Promise<void> => {
  const sessionManager = new RecordingBridgeSessionManager()
  fastify.decorate('recordingBridgeSessionManager', sessionManager)
  void fastify.register(cors, {
    origin: true
  })
  void fastify.register(websocket)
  fastify.addHook('onClose', async () => {
    await sessionManager.closeAll()
  })

  // Do not touch the following lines

  // This loads all plugins defined in plugins
  // those should be support plugins that are reused
  // through your application
  // eslint-disable-next-line no-void
  void fastify.register(AutoLoad, {
    dir: path.join(__dirname, 'plugins'),
    options: opts,
    forceESM: true
  })

  // This loads all plugins defined in routes
  // define your routes in one of these
  // eslint-disable-next-line no-void
  void fastify.register(AutoLoad, {
    dir: path.join(__dirname, 'routes'),
    options: opts,
    forceESM: true
  })
}

export default app
export { app, options }
