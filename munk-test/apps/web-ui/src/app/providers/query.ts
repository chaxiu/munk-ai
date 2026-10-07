import type { App } from 'vue'
import { VueQueryPlugin } from '@tanstack/vue-query'

import { queryClient } from '@/shared/query/queryClient'

export function installQuery(app: App<Element>): void {
  app.use(VueQueryPlugin, {
    queryClient,
    enableDevtoolsV6Plugin: false,
  })
}
