export type TimeValue = string | null | undefined

export interface RelativeTimeMessages {
  justNow: string
}

export interface DurationFormatMessages {
  milliseconds: (value: string) => string
  seconds: (value: string) => string
  minutesSeconds: (minutes: string, seconds: string) => string
}

const ABSOLUTE_DATE_TIME_OPTIONS: Intl.DateTimeFormatOptions = {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
}

const TOOLTIP_DATE_TIME_OPTIONS: Intl.DateTimeFormatOptions = {
  ...ABSOLUTE_DATE_TIME_OPTIONS,
  timeZoneName: 'short',
}

const RELATIVE_UNITS: Array<{ unit: Intl.RelativeTimeFormatUnit, sizeMs: number }> = [
  { unit: 'year', sizeMs: 365 * 24 * 60 * 60 * 1000 },
  { unit: 'month', sizeMs: 30 * 24 * 60 * 60 * 1000 },
  { unit: 'week', sizeMs: 7 * 24 * 60 * 60 * 1000 },
  { unit: 'day', sizeMs: 24 * 60 * 60 * 1000 },
  { unit: 'hour', sizeMs: 60 * 60 * 1000 },
  { unit: 'minute', sizeMs: 60 * 1000 },
]

function fallbackTimeValue(value: TimeValue): string {
  if (typeof value === 'string' && value.trim()) {
    return value
  }
  return '-'
}

export function parseDate(value: TimeValue): Date | null {
  if (!value) {
    return null
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return null
  }
  return date
}

export function toDateTimeAttr(value: TimeValue): string | null {
  const date = parseDate(value)
  return date ? date.toISOString() : null
}

export function formatAbsoluteDateTime(value: TimeValue, locale: string): string {
  const date = parseDate(value)
  if (!date) {
    return fallbackTimeValue(value)
  }
  return new Intl.DateTimeFormat(locale, ABSOLUTE_DATE_TIME_OPTIONS).format(date)
}

export function formatTimeTooltip(value: TimeValue, locale: string): string {
  const date = parseDate(value)
  if (!date) {
    return fallbackTimeValue(value)
  }
  return new Intl.DateTimeFormat(locale, TOOLTIP_DATE_TIME_OPTIONS).format(date)
}

export function formatRelativeDateTime(
  value: TimeValue,
  locale: string,
  now: number | Date,
  messages: RelativeTimeMessages,
): string {
  const date = parseDate(value)
  if (!date) {
    return fallbackTimeValue(value)
  }

  const nowMs = now instanceof Date ? now.getTime() : now
  const diffMs = date.getTime() - nowMs
  const absMs = Math.abs(diffMs)
  if (absMs < 60 * 1000) {
    return messages.justNow
  }

  const relativeTimeFormat = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' })
  for (const { unit, sizeMs } of RELATIVE_UNITS) {
    if (absMs >= sizeMs) {
      const direction = diffMs < 0 ? -1 : 1
      const value = Math.floor(absMs / sizeMs) * direction
      return relativeTimeFormat.format(value, unit)
    }
  }

  return messages.justNow
}

export function formatDuration(
  value: number | null | undefined,
  locale: string,
  messages: DurationFormatMessages,
): string {
  if (value == null || Number.isNaN(value)) {
    return '-'
  }

  const integerFormatter = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 })
  const decimalFormatter = new Intl.NumberFormat(locale, { maximumFractionDigits: 1 })

  if (value < 1000) {
    return messages.milliseconds(integerFormatter.format(value))
  }

  const totalSeconds = value / 1000
  if (totalSeconds < 60) {
    return messages.seconds(decimalFormatter.format(totalSeconds))
  }

  const minutes = Math.floor(totalSeconds / 60)
  const remainingSeconds = Math.round(totalSeconds % 60)
  return messages.minutesSeconds(
    integerFormatter.format(minutes),
    integerFormatter.format(remainingSeconds),
  )
}
