import fs from 'node:fs/promises'

import { RecordingBridgeSessionError } from './recording_bridge_errors.js'

export async function ensureServerBinary (filePath: string): Promise<void> {
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
