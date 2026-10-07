import { computed, onUnmounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import {
  formatAbsoluteDateTime,
  formatDuration,
  formatRelativeDateTime,
  formatTimeTooltip,
  toDateTimeAttr,
  type TimeValue,
} from './formatters'

const RELATIVE_REFRESH_INTERVAL_MS = 60 * 1000

export function useTime(options: { relative?: boolean } = {}) {
  const { locale, t } = useI18n()
  const now = ref(Date.now())
  let timer: number | null = null

  if (options.relative && typeof window !== 'undefined' && timer === null) {
    timer = window.setInterval(() => {
      now.value = Date.now()
    }, RELATIVE_REFRESH_INTERVAL_MS)
  }

  onUnmounted(() => {
    if (timer !== null) {
      window.clearInterval(timer)
    }
  })

  const relativeMessages = computed(() => ({
    justNow: t('time.relative.justNow'),
  }))

  const durationMessages = computed(() => ({
    milliseconds: (value: string) => t('time.duration.milliseconds', { value }),
    seconds: (value: string) => t('time.duration.seconds', { value }),
    minutesSeconds: (minutes: string, seconds: string) => t('time.duration.minutesSeconds', { minutes, seconds }),
  }))

  return {
    absolute: (value: TimeValue) => formatAbsoluteDateTime(value, locale.value),
    relative: (value: TimeValue) => formatRelativeDateTime(value, locale.value, now.value, relativeMessages.value),
    duration: (value: number | null | undefined) => formatDuration(value, locale.value, durationMessages.value),
    tooltip: (value: TimeValue) => formatTimeTooltip(value, locale.value),
    datetime: (value: TimeValue) => toDateTimeAttr(value),
  }
}
