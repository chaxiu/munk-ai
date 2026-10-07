import { describe, expect, it } from 'vitest'

import {
  buildCronFromTemplate,
  computeNextRunPreview,
  describeCronTemplate,
  parseCronTemplate,
  validateCronExpr,
} from '../cron'

describe('cron helpers', () => {
  it('recognizes supported template expressions', () => {
    expect(parseCronTemplate('0 9 * * 1-5')).toMatchObject({
      mode: 'weekdays',
      minute: '0',
      hour: '9',
    })

    expect(parseCronTemplate('30 8 * * 2')).toMatchObject({
      mode: 'weekly',
      minute: '30',
      hour: '8',
      weekday: '2',
    })

    expect(parseCronTemplate('15 7 12 * *')).toMatchObject({
      mode: 'monthly',
      minute: '15',
      hour: '7',
      dayOfMonth: '12',
    })
  })

  it('falls back to custom mode for unsupported expressions', () => {
    expect(parseCronTemplate('*/15 9 * * *')).toMatchObject({
      mode: 'custom',
      rawExpr: '*/15 9 * * *',
    })
  })

  it('builds a 5-field cron expression from template state', () => {
    expect(buildCronFromTemplate({
      mode: 'monthly',
      minute: '30',
      hour: '8',
      weekday: '1',
      dayOfMonth: '12',
      rawExpr: '',
    })).toBe('30 8 12 * *')
  })

  it('validates required, invalid, and valid expressions', () => {
    expect(validateCronExpr('')).toBe('required')
    expect(validateCronExpr('bad cron')).toBe('field_count')
    expect(validateCronExpr('61 9 * * *')).toBe('invalid')
    expect(validateCronExpr('0 9 * * 1-5')).toBeNull()
  })

  it('computes next run previews with timezone awareness', () => {
    expect(
      computeNextRunPreview(
        '0 9 * * 1-5',
        'Asia/Shanghai',
        new Date('2026-06-01T00:30:00Z'),
      ),
    ).toBe('2026-06-01T01:00:00.000Z')
  })

  it('describes template states with provided labels', () => {
    const text = describeCronTemplate({
      mode: 'weekly',
      minute: '0',
      hour: '9',
      weekday: '2',
      dayOfMonth: '1',
      rawExpr: '0 9 * * 2',
    }, {
      daily: (timeLabel) => `daily ${timeLabel}`,
      weekdays: (timeLabel) => `weekdays ${timeLabel}`,
      weekly: (weekdayLabel, timeLabel) => `${weekdayLabel} ${timeLabel}`,
      monthly: (dayLabel, timeLabel) => `${dayLabel} ${timeLabel}`,
      custom: (expression) => expression,
      weekdayLabels: {
        0: 'Sun',
        1: 'Mon',
        2: 'Tue',
        3: 'Wed',
        4: 'Thu',
        5: 'Fri',
        6: 'Sat',
      },
      dayOfMonth: (day) => `Day ${day}`,
    })

    expect(text).toBe('Tue 09:00')
  })
})
