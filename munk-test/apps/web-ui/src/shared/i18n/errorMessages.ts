import { i18n } from './index'

export function translateErrorCode(code: string, fallbackMessage: string): string {
  const key = `errors.${code}`
  if (i18n.global.te(key)) {
    const translated = i18n.global.t(key)
    if (!fallbackMessage || fallbackMessage === translated) {
      return translated
    }
    return `${translated} ${fallbackMessage}`
  }
  return fallbackMessage
}
