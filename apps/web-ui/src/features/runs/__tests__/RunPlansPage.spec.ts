import { computed, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { typedViFn } from '@/shared/testing/typedViFn'

import RunPlansPage from '../pages/RunPlansPage.vue'
import { i18n, setLocale } from '@/shared/i18n'
import { schedulesKeys } from '@/features/schedules/queries/schedulesKeys'

const { pushMock, submitRunPlansMock, createScheduleMock, invalidateQueriesMock } = vi.hoisted(() => ({
  pushMock: vi.fn(async () => undefined),
  submitRunPlansMock: vi.fn(async () => ({
    operation_id: 'op-batch-1',
    status: 'queued',
    verification_verdict: null,
  })),
  createScheduleMock: vi.fn(async () => ({
    schedule_id: 'schedule-1',
    name: 'Morning run',
    app_id: 'app-1',
    plan_ids: ['plan-1', 'plan-2'],
    device_ref: 'device-a',
    cron_expr: '0 9 * * 1-5',
    enabled: true,
    timezone: 'Asia/Shanghai',
    next_run_at: null,
    last_run_at: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    recent_runs: [],
    queued_run_count: 0,
    active_schedule_run_id: null,
    latest_operation_id: null,
  })),
  invalidateQueriesMock: vi.fn(async () => undefined),
}))

const appsState = ref([
  { app_id: 'app-1', platform: 'android' },
  { app_id: 'app-2', platform: 'android' },
])
const devicesState = ref([
  { device_ref: 'device-a', display_name: 'Pixel 8', platform: 'android' },
  { device_ref: 'device-b', display_name: 'Pixel 9', platform: 'android' },
])
const plansState = ref([
  { plan_id: 'plan-1', plan_name: 'Settings coverage', case_count: 3, app_id: 'app-1' },
  { plan_id: 'plan-2', plan_name: 'Checkout coverage', case_count: 5, app_id: 'app-1' },
])

vi.mock('vue-router', async () => {
  const actual = await vi.importActual<typeof import('vue-router')>('vue-router')
  return {
    ...actual,
    useRouter: () => ({
      push: pushMock,
    }),
  }
})

vi.mock('@tanstack/vue-query', async () => {
  const actual = await vi.importActual<typeof import('@tanstack/vue-query')>('@tanstack/vue-query')
  return {
    ...actual,
    useQueryClient: () => ({
      invalidateQueries: invalidateQueriesMock,
    }),
  }
})

vi.mock('@/shared/api/workflows', () => ({
  submitRunPlans: submitRunPlansMock,
}))

vi.mock('@/shared/api/schedules', () => ({
  createSchedule: createScheduleMock,
}))

vi.mock('@/features/apps/queries/useAppsQuery', () => ({
  useAppsQuery: () => ({
    data: computed(() => appsState.value),
    isFetching: ref(false),
    error: ref(null),
  }),
}))

vi.mock('@/features/devices/queries/useDevicesQuery', () => ({
  useDevicesQuery: () => ({
    data: computed(() => devicesState.value),
    isFetching: ref(false),
    error: ref(null),
  }),
}))

vi.mock('@/features/tests/queries/usePlansQuery', () => ({
  usePlansQuery: () => ({
    data: computed(() => ({
      items: plansState.value,
      total: plansState.value.length,
      limit: 100,
      offset: 0,
    })),
    isFetching: ref(false),
    error: ref(null),
  }),
}))

function mountPage() {
  return mount(RunPlansPage, {
    global: {
      plugins: [i18n],
      stubs: {
        UiSelect: {
          props: ['modelValue', 'options', 'placeholder', 'disabled'],
          emits: ['update:modelValue'],
          template: `
            <select :value="modelValue" :disabled="disabled" @change="$emit('update:modelValue', $event.target.value)">
              <option value="">{{ placeholder }}</option>
              <option v-for="option in options" :key="option.value" :value="option.value">{{ option.label }}</option>
            </select>
          `,
        },
        CronEditorField: {
          props: ['modelValue', 'label', 'placeholder', 'disabled'],
          emits: ['update:modelValue', 'validation-change'],
          template: `
            <label>
              <span>{{ label }}</span>
              <span>Visual Helper</span>
              <input
                type="text"
                :value="modelValue"
                :placeholder="placeholder"
                :disabled="disabled"
                :aria-label="label"
                @input="$emit('update:modelValue', $event.target.value); $emit('validation-change', $event.target.value.includes('bad'))"
              >
            </label>
          `,
        },
      },
    },
  })
}

describe('RunPlansPage', () => {
  beforeEach(() => {
    setLocale('en-US')
    vi.spyOn(Intl, 'DateTimeFormat').mockReturnValue({
      resolvedOptions: () => ({
        locale: 'en-US',
        calendar: 'gregory',
        numberingSystem: 'latn',
        timeZone: 'Asia/Shanghai',
      }),
    } as Intl.DateTimeFormat)
    pushMock.mockClear()
    submitRunPlansMock.mockClear()
    createScheduleMock.mockClear()
    invalidateQueriesMock.mockClear()
    appsState.value = [
      { app_id: 'app-1', platform: 'android' },
      { app_id: 'app-2', platform: 'android' },
    ]
    devicesState.value = [
      { device_ref: 'device-a', display_name: 'Pixel 8', platform: 'android' },
      { device_ref: 'device-b', display_name: 'Pixel 9', platform: 'android' },
    ]
    plansState.value = [
      { plan_id: 'plan-1', plan_name: 'Settings coverage', case_count: 3, app_id: 'app-1' },
      { plan_id: 'plan-2', plan_name: 'Checkout coverage', case_count: 5, app_id: 'app-1' },
    ]
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders selected plans in click order', async () => {
    const wrapper = mountPage()

    await flushPromises()

    const selects = wrapper.findAll('select')
    await selects[0]!.setValue('app-1')
    await flushPromises()
    await selects[1]!.setValue('device-a')
    await flushPromises()

    await wrapper.findAll('button').find((button) => button.text().includes('Checkout coverage'))?.trigger('click')
    await flushPromises()
    await wrapper.findAll('button').find((button) => button.text().includes('Settings coverage'))?.trigger('click')
    await flushPromises()

    const selectedArticles = wrapper.findAll('article')
    expect(selectedArticles).toHaveLength(2)
    expect(selectedArticles[0]?.text()).toContain('Checkout coverage')
    expect(selectedArticles[1]?.text()).toContain('Settings coverage')
    expect(wrapper.text()).toContain('Execution Order')
    expect(wrapper.text()).toContain('Task Name')
    expect(wrapper.text()).toContain('Enable schedule')
    expect(wrapper.text()).not.toContain('Cron Expression')
  })

  it('submits selected plans and navigates to parent run detail', async () => {
    const wrapper = mountPage()

    await flushPromises()

    const selects = wrapper.findAll('select')
    await selects[0]!.setValue('app-1')
    await flushPromises()
    await selects[1]!.setValue('device-a')
    await flushPromises()

    await wrapper.findAll('button').find((button) => button.text().includes('Settings coverage'))?.trigger('click')
    await flushPromises()
    await wrapper.findAll('button').find((button) => button.text().includes('Checkout coverage'))?.trigger('click')
    await flushPromises()

    await wrapper.findAll('button').find((button) => button.text().includes('Start Run'))?.trigger('click')
    await flushPromises()

    expect(submitRunPlansMock).toHaveBeenCalledWith({
      app_id: 'app-1',
      plan_ids: ['plan-1', 'plan-2'],
      device_ref: 'device-a',
      fail_fast: false,
      headless: false,
    }, { wait: false, detach: false })
    expect(pushMock).toHaveBeenCalledWith('/runs/op-batch-1')
    expect(createScheduleMock).not.toHaveBeenCalled()
  })

  it('shows cron input only when schedule mode is enabled and creates schedule', async () => {
    const wrapper = mountPage()

    await flushPromises()

    const textInputsBefore = wrapper.findAll('input[type="text"]')
    await textInputsBefore[0]!.setValue('Morning run')

    const checkbox = wrapper.find('input[type="checkbox"]')
    await checkbox.setValue(true)
    await flushPromises()

    expect(wrapper.text()).toContain('Cron Expression')
    expect(wrapper.text()).toContain('Visual Helper')

    const selects = wrapper.findAll('select')
    await selects[0]!.setValue('app-1')
    await flushPromises()
    await selects[1]!.setValue('device-a')
    await flushPromises()

    await wrapper.findAll('button').find((button) => button.text().includes('Settings coverage'))?.trigger('click')
    await flushPromises()
    await wrapper.findAll('button').find((button) => button.text().includes('Checkout coverage'))?.trigger('click')
    await flushPromises()

    const cronInput = wrapper.find('input[aria-label="Cron Expression"]')
    await cronInput.setValue('0 9 * * 1-5')
    await flushPromises()

    await wrapper.findAll('button').find((button) => button.text().includes('Create Schedule'))?.trigger('click')
    await flushPromises()

    expect(createScheduleMock).toHaveBeenCalledWith({
      name: 'Morning run',
      app_id: 'app-1',
      plan_ids: ['plan-1', 'plan-2'],
      device_ref: 'device-a',
      timezone: 'Asia/Shanghai',
      cron_expr: '0 9 * * 1-5',
      enabled: true,
      fail_fast: false,
      headless: false,
    })
    expect(invalidateQueriesMock).toHaveBeenCalledWith({ queryKey: schedulesKeys.list() })
    expect(invalidateQueriesMock).toHaveBeenCalledWith({ queryKey: schedulesKeys.all })
    expect(invalidateQueriesMock.mock.invocationCallOrder[0]).toBeLessThan(pushMock.mock.invocationCallOrder[0]!)
    expect(submitRunPlansMock).not.toHaveBeenCalled()
    expect(pushMock).toHaveBeenCalledWith('/schedules')
  })

  it('disables schedule submit when cron editor reports a local validation error', async () => {
    const wrapper = mountPage()

    await flushPromises()

    await wrapper.find('input[type="checkbox"]').setValue(true)
    await flushPromises()

    const selects = wrapper.findAll('select')
    await selects[0]!.setValue('app-1')
    await flushPromises()
    await selects[1]!.setValue('device-a')
    await flushPromises()

    await wrapper.findAll('button').find((button) => button.text().includes('Settings coverage'))?.trigger('click')
    await flushPromises()

    await wrapper.find('input[aria-label="Cron Expression"]').setValue('bad cron')
    await flushPromises()

    const submitButton = wrapper.findAll('button').find((button) => button.text().includes('Create Schedule'))
    expect(submitButton?.attributes('disabled')).toBeDefined()

    await submitButton?.trigger('click')
    await flushPromises()

    expect(createScheduleMock).not.toHaveBeenCalled()
    expect(pushMock).not.toHaveBeenCalled()
  })
})
