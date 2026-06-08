import { createRouter, createWebHistory } from 'vue-router'

import { i18n } from '@/shared/i18n'
import { logger } from '@/shared/logging/logger'
import { routes } from './routes'

export const router = createRouter({
  history: createWebHistory('/'),
  routes,
})

router.afterEach((to) => {
  const defaultTitle = i18n.global.t('app.title')
  const pageTitle = typeof to.meta.navLabel === 'string'
    ? i18n.global.t(to.meta.navLabel)
    : typeof to.meta.title === 'string'
      ? to.meta.title
      : defaultTitle

  document.title = pageTitle === defaultTitle ? defaultTitle : `${pageTitle} · ${defaultTitle}`

  logger.info({
    scope: 'router',
    event: 'navigation.success',
    message: `Navigated to ${to.fullPath}`,
    context: {
      routeName: to.name,
      feature: to.meta.feature,
    },
  })
})

router.onError((error, to) => {
  logger.error({
    scope: 'router',
    event: 'navigation.error',
    message: error.message,
    context: {
      to: to.fullPath,
    },
  })
})
