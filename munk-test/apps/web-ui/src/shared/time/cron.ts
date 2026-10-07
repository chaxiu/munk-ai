import { CronExpressionParser } from 'cron-parser'

export type CronTemplateMode = 'daily' | 'weekdays' | 'weekly' | 'monthly' | 'custom'
export type CronWeekday = '0' | '1' | '2' | '3' | '4' | '5' | '6'

export type CronTemplateState = {
  mode: CronTemplateMode
  minute: string
  hour: string
  weekday: CronWeekday
  dayOfMonth: string
  rawExpr: string
}

export type CronValidationErrorCode = 'required' | 'field_count' | 'invalid'

export type CronDescriptionLabels = {
  daily: (timeLabel: string) => string
  weekdays: (timeLabel: string) => string
  weekly: (weekdayLabel: string, timeLabel: string) => string
  monthly: (dayLabel: string, timeLabel: string) => string
  custom: (expression: string) => string
  weekdayLabels: Record<CronWeekday, string>
  dayOfMonth: (day: string) => string
}

export const DEFAULT_CRON_TEMPLATE_STATE: CronTemplateState = {
  mode: 'weekdays',
  minute: '0',
  hour: '9',
  weekday: '1',
  dayOfMonth: '1',
  rawExpr: '0 9 * * 1-5',
}

export function normalizeCronExpr(value: string): string {
  return value.trim().split(/\s+/).join(' ')
}

export function buildCronFromTemplate(state: CronTemplateState): string {
  const minute = normalizeMinute(state.minute)
  const hour = normalizeHour(state.hour)

  switch (state.mode) {
    case 'daily':
      return `${minute} ${hour} * * *`
    case 'weekdays':
      return `${minute} ${hour} * * 1-5`
    case 'weekly':
      return `${minute} ${hour} * * ${normalizeWeekday(state.weekday)}`
    case 'monthly':
      return `${minute} ${hour} ${normalizeDayOfMonth(state.dayOfMonth)} * *`
    case 'custom':
      return normalizeCronExpr(state.rawExpr)
  }
}

export function parseCronTemplate(
  value: string,
  fallback: CronTemplateState = DEFAULT_CRON_TEMPLATE_STATE,
): CronTemplateState {
  const normalized = normalizeCronExpr(value)
  if (!normalized) {
    return { ...fallback }
  }

  const parts = normalized.split(' ')
  if (parts.length !== 5) {
    return {
      ...fallback,
      mode: 'custom',
      rawExpr: normalized,
    }
  }

  const [minute, hour, dayOfMonth, month, dayOfWeek] = parts as [string, string, string, string, string]
  const normalizedMinute = parseSingleNumber(minute, 0, 59)
  const normalizedHour = parseSingleNumber(hour, 0, 23)

  if (normalizedMinute == null || normalizedHour == null) {
    return {
      ...fallback,
      mode: 'custom',
      rawExpr: normalized,
    }
  }

  if (month !== '*') {
    return {
      ...fallback,
      minute: String(normalizedMinute),
      hour: String(normalizedHour),
      mode: 'custom',
      rawExpr: normalized,
    }
  }

  if (dayOfMonth === '*' && dayOfWeek === '*') {
    return {
      mode: 'daily',
      minute: String(normalizedMinute),
      hour: String(normalizedHour),
      weekday: fallback.weekday,
      dayOfMonth: fallback.dayOfMonth,
      rawExpr: normalized,
    }
  }

  if (dayOfMonth === '*' && dayOfWeek === '1-5') {
    return {
      mode: 'weekdays',
      minute: String(normalizedMinute),
      hour: String(normalizedHour),
      weekday: '1',
      dayOfMonth: fallback.dayOfMonth,
      rawExpr: normalized,
    }
  }

  const normalizedWeekday = parseSingleWeekday(dayOfWeek)
  if (dayOfMonth === '*' && normalizedWeekday != null) {
    return {
      mode: 'weekly',
      minute: String(normalizedMinute),
      hour: String(normalizedHour),
      weekday: normalizedWeekday,
      dayOfMonth: fallback.dayOfMonth,
      rawExpr: normalized,
    }
  }

  const normalizedDayOfMonth = parseSingleNumber(dayOfMonth, 1, 31)
  if (dayOfWeek === '*' && normalizedDayOfMonth != null) {
    return {
      mode: 'monthly',
      minute: String(normalizedMinute),
      hour: String(normalizedHour),
      weekday: fallback.weekday,
      dayOfMonth: String(normalizedDayOfMonth),
      rawExpr: normalized,
    }
  }

  return {
    ...fallback,
    minute: String(normalizedMinute),
    hour: String(normalizedHour),
    mode: 'custom',
    rawExpr: normalized,
  }
}

export function validateCronExpr(value: string): CronValidationErrorCode | null {
  const normalized = normalizeCronExpr(value)
  if (!normalized) {
    return 'required'
  }

  const parts = normalized.split(' ')
  if (parts.length !== 5) {
    return 'field_count'
  }

  try {
    CronExpressionParser.parse(normalized, { strict: false })
    return null
  } catch {
    return 'invalid'
  }
}

export function computeNextRunPreview(
  value: string,
  timezone: string,
  currentDate: Date = new Date(),
): string | null {
  const normalized = normalizeCronExpr(value)
  if (validateCronExpr(normalized)) {
    return null
  }

  try {
    const expression = CronExpressionParser.parse(normalized, {
      currentDate,
      tz: timezone,
      strict: false,
    })
    return expression.next().toDate().toISOString()
  } catch {
    return null
  }
}

export function describeCronTemplate(
  state: CronTemplateState,
  labels: CronDescriptionLabels,
): string {
  const timeLabel = `${pad2(state.hour)}:${pad2(state.minute)}`

  switch (state.mode) {
    case 'daily':
      return labels.daily(timeLabel)
    case 'weekdays':
      return labels.weekdays(timeLabel)
    case 'weekly':
      return labels.weekly(labels.weekdayLabels[normalizeWeekday(state.weekday)], timeLabel)
    case 'monthly':
      return labels.monthly(labels.dayOfMonth(normalizeDayOfMonth(state.dayOfMonth)), timeLabel)
    case 'custom':
      return labels.custom(normalizeCronExpr(state.rawExpr))
  }
}

function parseSingleNumber(value: string, min: number, max: number): number | null {
  if (!/^\d+$/.test(value)) {
    return null
  }
  const parsed = Number(value)
  if (!Number.isInteger(parsed) || parsed < min || parsed > max) {
    return null
  }
  return parsed
}

function parseSingleWeekday(value: string): CronWeekday | null {
  const parsed = parseSingleNumber(value, 0, 7)
  if (parsed == null) {
    return null
  }
  return String(parsed === 7 ? 0 : parsed) as CronWeekday
}

function normalizeMinute(value: string): string {
  const parsed = parseSingleNumber(value, 0, 59)
  return String(parsed ?? 0)
}

function normalizeHour(value: string): string {
  const parsed = parseSingleNumber(value, 0, 23)
  return String(parsed ?? 0)
}

function normalizeDayOfMonth(value: string): string {
  const parsed = parseSingleNumber(value, 1, 31)
  return String(parsed ?? 1)
}

function normalizeWeekday(value: string): CronWeekday {
  return parseSingleWeekday(value) ?? '1'
}

function pad2(value: string): string {
  return value.padStart(2, '0')
}
