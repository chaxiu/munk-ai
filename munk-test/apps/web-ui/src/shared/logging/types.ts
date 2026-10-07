export type LogLevel = 'debug' | 'info' | 'warn' | 'error'

export interface LogEntry {
  timestamp: string
  level: LogLevel
  scope: string
  event: string
  message: string
  context?: Record<string, unknown>
}

export interface LogSink {
  write(entry: LogEntry): void
}
