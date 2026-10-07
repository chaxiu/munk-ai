import { describe, expect, it } from 'vitest'

import {
  formatAbsoluteDateTime,
  formatDuration,
  formatRelativeDateTime,
  formatTimeTooltip,
  parseDate,
  toDateTimeAttr,
} from '../formatters'

const relativeMessages = {
  justNow: 'just now',
}

const durationMessages = {
  milliseconds: (value: string) => `${value} ms`,
  seconds: (value: string) => `${value} sec`,
  minutesSeconds: (minutes: string, seconds: string) => `${minutes} min ${seconds} sec`,
}

describe('time formatters', () => {
  it('parses timezone-aware ISO timestamps', () => {
    expect(parseDate('2026-05-19T21:07:15.413380+00:00')?.toISOString()).toBe('2026-05-19T21:07:15.413Z')
  })

  it('returns normalized datetime attrs for valid timestamps', () => {
    expect(toDateTimeAttr('2026-05-19T21:07:15.413380+00:00')).toBe('2026-05-19T21:07:15.413Z')
    expect(toDateTimeAttr('not-a-date')).toBeNull()
  })

  it('formats absolute timestamps with locale instead of raw ISO', () => {
    const raw = '2026-05-19T21:07:15.413380+00:00'
    const enValue = formatAbsoluteDateTime(raw, 'en-US')
    const zhValue = formatAbsoluteDateTime(raw, 'zh-CN')

    expect(enValue).not.toBe(raw)
    expect(zhValue).not.toBe(raw)
    expect(enValue).not.toBe(zhValue)
  })

  it('formats tooltip timestamps with timezone details', () => {
    const value = formatTimeTooltip('2026-05-19T21:07:15.413380+00:00', 'en-US')
    expect(value).toContain('2026')
    expect(value).not.toBe('2026-05-19T21:07:15.413380+00:00')
  })

  it('formats relative timestamps around key boundaries', () => {
    const now = new Date('2026-05-20T10:00:00Z')

    expect(formatRelativeDateTime('2026-05-20T09:59:30Z', 'en-US', now, relativeMessages)).toBe('just now')
    expect(formatRelativeDateTime('2026-05-20T09:58:00Z', 'en-US', now, relativeMessages)).toBe('2 minutes ago')
    expect(formatRelativeDateTime('2026-05-20T09:00:00Z', 'en-US', now, relativeMessages)).toBe('1 hour ago')
    expect(formatRelativeDateTime('2026-05-19T10:00:00Z', 'en-US', now, relativeMessages)).toBe('yesterday')
  })

  it('formats durations consistently', () => {
    expect(formatDuration(500, 'en-US', durationMessages)).toBe('500 ms')
    expect(formatDuration(1500, 'en-US', durationMessages)).toBe('1.5 sec')
    expect(formatDuration(125000, 'en-US', durationMessages)).toBe('2 min 5 sec')
    expect(formatDuration(null, 'en-US', durationMessages)).toBe('-')
  })
})
