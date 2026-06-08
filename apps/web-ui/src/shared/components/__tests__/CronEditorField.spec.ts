import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import CronEditorField from '../CronEditorField.vue'
import { i18n, setLocale } from '@/shared/i18n'

describe('CronEditorField', () => {
  let resolvedOptionsSpy: ReturnType<typeof vi.spyOn> | null = null

  beforeEach(() => {
    setLocale('en-US')
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-06-01T00:30:00Z'))
  })

  afterEach(() => {
    resolvedOptionsSpy?.mockRestore()
    resolvedOptionsSpy = null
    vi.useRealTimers()
  })

  function mountField(props: Record<string, unknown> = {}) {
    return mount(CronEditorField, {
      props,
      global: {
        plugins: [i18n],
        stubs: {
          UiField: {
            props: ['label', 'hint', 'error'],
            template: `
              <label>
                <span>{{ label }}</span>
                <span v-if="hint">{{ hint }}</span>
                <slot />
                <p v-if="error">{{ error }}</p>
              </label>
            `,
          },
          UiInput: {
            props: ['modelValue', 'placeholder', 'disabled', 'ariaLabel'],
            emits: ['update:modelValue'],
            template: `
              <input
                v-bind="$attrs"
                :value="modelValue"
                :placeholder="placeholder"
                :disabled="disabled"
                :aria-label="ariaLabel"
                @input="$emit('update:modelValue', $event.target.value)"
              >
            `,
          },
          UiSelect: {
            props: ['modelValue', 'options', 'disabled', 'placeholder'],
            emits: ['update:modelValue'],
            template: `
              <select
                :value="modelValue"
                :disabled="disabled"
                @change="$emit('update:modelValue', $event.target.value)"
              >
                <option value="">{{ placeholder }}</option>
                <option v-for="option in options" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
            `,
          },
        },
      },
    })
  }

  it('renders a recognized template with summary, timezone, and next run preview', () => {
    const wrapper = mountField({
      modelValue: '0 9 * * 1-5',
      timezone: 'Asia/Shanghai',
    })

    expect(wrapper.text()).toContain('Schedule Template')
    expect(wrapper.text()).toContain('Runs every weekday at 09:00')
    expect(wrapper.text()).toContain('0 9 * * 1-5')
    expect(wrapper.text()).toContain('Asia/Shanghai')
    expect(wrapper.text()).not.toContain('Unavailable until the expression is valid')
  })

  it('falls back to the browser timezone when the schedule timezone is empty', () => {
    resolvedOptionsSpy = vi
      .spyOn(Intl.DateTimeFormat.prototype, 'resolvedOptions')
      .mockReturnValue({
        locale: 'en-US',
        calendar: 'gregory',
        numberingSystem: 'latn',
        timeZone: 'Asia/Shanghai',
        year: 'numeric',
        month: 'numeric',
        day: 'numeric',
      } as Intl.ResolvedDateTimeFormatOptions)

    const wrapper = mountField({
      modelValue: '0 9 * * 1-5',
      timezone: '',
    })

    expect(wrapper.text()).toContain('Asia/Shanghai')
    expect(wrapper.text()).not.toContain('Unavailable until the expression is valid')
  })

  it('updates the emitted cron when switching to a template mode', async () => {
    const wrapper = mountField({
      modelValue: '0 9 * * 1-5',
    })

    const selects = wrapper.findAll('select')
    await selects[0]!.setValue('daily')
    await selects[2]!.setValue('15')

    const updates = wrapper.emitted('update:modelValue') ?? []
    expect(updates[updates.length - 1]).toEqual(['15 9 * * *'])
    expect(wrapper.text()).toContain('Runs every day at 09:15')
  })

  it('falls back to custom mode for unsupported cron expressions', () => {
    const wrapper = mountField({
      modelValue: '*/15 9 * * *',
      timezone: 'Asia/Shanghai',
    })

    expect(wrapper.text()).toContain('Runs by advanced cron: */15 9 * * *')
  })

  it('emits update:modelValue when the raw custom input changes', async () => {
    const wrapper = mountField({
      modelValue: '0 9 * * 1-5',
    })

    await wrapper.find('select').setValue('custom')
    expect(wrapper.text()).toContain('Runs by advanced cron: 0 9 * * 1-5')
    expect(wrapper.find('input[aria-label="Advanced Cron"]').exists()).toBe(true)
    await wrapper.find('input[aria-label="Advanced Cron"]').setValue('30 11 * * 1')

    const updates = wrapper.emitted('update:modelValue') ?? []
    expect(updates[updates.length - 1]).toEqual(['30 11 * * 1'])
  })

  it('shows an internal validation error for invalid custom cron input', async () => {
    const wrapper = mountField({
      modelValue: '0 9 * * 1-5',
    })

    await wrapper.find('select').setValue('custom')
    await wrapper.find('input[aria-label="Advanced Cron"]').setValue('bad cron')

    expect(wrapper.text()).toContain('Cron expression must contain 5 fields.')

    const events = wrapper.emitted('validation-change') ?? []
    expect(events[events.length - 1]).toEqual([true])
  })

  it('keeps the external error higher priority than internal validation', async () => {
    const wrapper = mountField({
      modelValue: '0 9 * * 1-5',
      error: 'Backend rejected cron',
    })

    await wrapper.find('select').setValue('custom')
    await wrapper.find('input[aria-label="Advanced Cron"]').setValue('bad cron')

    expect(wrapper.text()).toContain('Backend rejected cron')
    expect(wrapper.text()).not.toContain('Cron expression must contain 5 fields.')
  })

  it('disables template controls and raw input when disabled is true', async () => {
    const wrapper = mountField({
      modelValue: 'bad cron',
      disabled: true,
    })

    expect(wrapper.find('select').attributes('disabled')).toBeDefined()
    expect(wrapper.find('input[aria-label="Advanced Cron"]').attributes('disabled')).toBeDefined()
  })
})
