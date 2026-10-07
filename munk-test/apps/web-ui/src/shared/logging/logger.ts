import { ConsoleSink } from './sinks/consoleSink'
import type { LogEntry, LogLevel, LogSink } from './types'

const levelOrder: Record<LogLevel, number> = {
  debug: 10,
  info: 20,
  warn: 30,
  error: 40,
}

class Logger {
  private readonly sinks: LogSink[] = [new ConsoleSink()]
  private level: LogLevel = import.meta.env.DEV ? 'debug' : 'info'

  setLevel(level: LogLevel): void {
    this.level = level
  }

  private shouldWrite(level: LogLevel): boolean {
    return levelOrder[level] >= levelOrder[this.level]
  }

  write(entry: Omit<LogEntry, 'timestamp'> & { level: LogLevel }): void {
    if (!this.shouldWrite(entry.level)) {
      return
    }
    const fullEntry: LogEntry = {
      timestamp: new Date().toISOString(),
      ...entry,
    }
    for (const sink of this.sinks) {
      sink.write(fullEntry)
    }
  }

  debug(entry: Omit<LogEntry, 'timestamp' | 'level'>): void {
    this.write({ ...entry, level: 'debug' })
  }

  info(entry: Omit<LogEntry, 'timestamp' | 'level'>): void {
    this.write({ ...entry, level: 'info' })
  }

  warn(entry: Omit<LogEntry, 'timestamp' | 'level'>): void {
    this.write({ ...entry, level: 'warn' })
  }

  error(entry: Omit<LogEntry, 'timestamp' | 'level'>): void {
    this.write({ ...entry, level: 'error' })
  }
}

export const logger = new Logger()
