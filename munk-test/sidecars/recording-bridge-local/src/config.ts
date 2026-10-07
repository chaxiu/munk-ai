import path from 'node:path'
import { fileURLToPath } from 'node:url'

export const DEFAULT_ADB_SERVER_HOST = '127.0.0.1'
export const DEFAULT_ADB_SERVER_PORT = 5037
export const DEFAULT_SCRCPY_SERVER_VERSION = '3.3.3'
export const DEFAULT_SCRCPY_SERVER_DEVICE_PATH = '/data/local/tmp/scrcpy-server.jar'
export const DEFAULT_VIDEO_BIT_RATE = 8_000_000
export const DEFAULT_MAX_SIZE = 0
export const DEFAULT_MAX_FPS = 0

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

export function defaultScrcpyServerBinaryPath (): string {
  return path.resolve(
    __dirname,
    '..',
    'node_modules',
    '@yume-chan',
    'fetch-scrcpy-server',
    'server.bin'
  )
}

export function resolveScrcpyServerBinaryPath (): string {
  return process.env.MUNK_SCRCPY_SERVER_BINARY ?? defaultScrcpyServerBinaryPath()
}
