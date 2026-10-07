import { computed } from 'vue'
import { useRoute } from 'vue-router'

import { i18n } from '@/shared/i18n'
import { theme } from '@/shared/theme/useTheme'

export function useLoggingContext() {
  const route = useRoute()

  return computed(() => ({
    routeName: typeof route.name === 'string' ? route.name : undefined,
    path: route.fullPath,
    feature: typeof route.meta.feature === 'string' ? route.meta.feature : undefined,
    locale: i18n.global.locale.value,
    theme: theme.value,
  }))
}
