import type { App } from 'vue'

import { logger } from '@/shared/logging/logger'

export function installLogger(_app: App<Element>): void {
  window.addEventListener('error', (event) => {
    logger.error({
      scope: 'app',
      event: 'window.error',
      message: event.message || 'Unhandled window error',
      context: {
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
      },
    })
  })

  window.addEventListener('unhandledrejection', (event) => {
    const reason = event.reason instanceof Error ? event.reason.message : String(event.reason)
    logger.error({
      scope: 'app',
      event: 'window.unhandledrejection',
      message: reason,
    })
  })
}
