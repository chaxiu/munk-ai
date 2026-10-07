import { createI18n } from 'vue-i18n'

import type { SupportedLocale } from './messageKeys'
import { enUS } from './locales/en-US'
import { zhCN } from './locales/zh-CN'

export function resolveInitialLocale(): SupportedLocale {
  const saved = typeof window !== 'undefined' ? window.localStorage.getItem('munk-ui-locale') : null
  if (saved === 'zh-CN' || saved === 'en-US') {
    return saved
  }
  if (typeof navigator !== 'undefined' && navigator.language.toLowerCase().startsWith('zh')) {
    return 'zh-CN'
  }
  return 'en-US'
}

export const i18n = createI18n({
  legacy: false,
  locale: resolveInitialLocale(),
  fallbackLocale: 'en-US',
  messages: {
    'zh-CN': zhCN,
    'en-US': enUS,
  },
})

export function setLocale(locale: SupportedLocale): void {
  i18n.global.locale.value = locale
  window.localStorage.setItem('munk-ui-locale', locale)
}
