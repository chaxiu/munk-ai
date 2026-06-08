import type { App } from 'vue'

import { initializeTheme } from '@/shared/theme/useTheme'

export function installTheme(_app: App<Element>): void {
  initializeTheme()
}
