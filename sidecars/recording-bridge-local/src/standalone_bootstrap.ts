import Fastify from 'fastify'

import app from './app.js'

function resolveListenPort (): number {
  const raw = process.env.PORT ?? '16900'
  const parsed = Number.parseInt(raw, 10)
  if (!Number.isInteger(parsed) || parsed <= 0) {
    throw new Error(`invalid PORT value for recording bridge: ${raw}`)
  }
  return parsed
}

async function main (): Promise<void> {
  const host = process.env.HOST ?? '127.0.0.1'
  const port = resolveListenPort()
  const server = Fastify({
    logger: {
      level: process.env.NODE_ENV === 'development' ? 'info' : 'warn'
    }
  })

  try {
    await server.register(app)
    await server.listen({ host, port })
  } catch (error) {
    try {
      await server.close()
    } catch {
      // Ignore secondary shutdown failures so the original startup error is preserved.
    }
    throw error
  }
}

await main()
