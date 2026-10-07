import type { LogEntry, LogSink } from '../types'

export class ConsoleSink implements LogSink {
  write(entry: LogEntry): void {
    const payload = {
      scope: entry.scope,
      event: entry.event,
      message: entry.message,
      context: entry.context,
    }
    if (entry.level === 'error') {
      console.error('[munk-ui]', payload)
      return
    }
    if (entry.level === 'warn') {
      console.warn('[munk-ui]', payload)
      return
    }
    if (entry.level === 'info') {
      console.info('[munk-ui]', payload)
      return
    }
    console.debug('[munk-ui]', payload)
  }
}
