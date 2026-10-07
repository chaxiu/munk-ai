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

function resolveParentPid (): number | null {
  const raw = process.env.MUNK_PARENT_PID
  if (!raw) {
    return null
  }
  const parsed = Number.parseInt(raw, 10)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null
}

function isProcessAlive (pid: number): boolean {
  try {
    process.kill(pid, 0)
    return true
  } catch (error) {
    return (error as NodeJS.ErrnoException).code === 'EPERM'
  }
}

async function main (): Promise<void> {
  const host = process.env.HOST ?? '127.0.0.1'
  const port = resolveListenPort()
  const parentPid = resolveParentPid()
  const server = Fastify({
    logger: {
      level: process.env.NODE_ENV === 'development' ? 'info' : 'warn'
    }
  })
  let parentWatchdog: NodeJS.Timeout | null = null

  try {
    await server.register(app)
    if (parentPid !== null) {
      parentWatchdog = setInterval(() => {
        if (isProcessAlive(parentPid)) {
          return
        }
        void server.close().finally(() => {
          process.exit(0)
        })
      }, 1000)
      parentWatchdog.unref()
    }
    await server.listen({ host, port })
  } catch (error) {
    if (parentWatchdog !== null) {
      clearInterval(parentWatchdog)
    }
    try {
      await server.close()
    } catch {
      // Ignore secondary shutdown failures so the original startup error is preserved.
    }
    throw error
  }
}

await main()
