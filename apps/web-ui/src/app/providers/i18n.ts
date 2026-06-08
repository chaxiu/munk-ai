import type { App } from 'vue'

import { i18n } from '@/shared/i18n'

export function installI18n(app: App<Element>): void {
  app.use(i18n)
}
