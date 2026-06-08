import { computed, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { typedViFn } from '@/shared/testing/typedViFn'

import ScheduleDetailPage from '../pages/ScheduleDetailPage.vue'
import { i18n, setLocale } from '@/shared/i18n'

const globalStubs = {
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
    props: ['modelValue', 'label', 'placeholder', 'disabled', 'timezone'],
          emits: ['update:modelValue', 'validation-change'],
    template: `
      <label>
        <span>{{ label }}</span>
        <span>Template Editor</span>
        <span>{{ timezone }}</span>
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
  RouterLink: {
    props: ['to'],
    template: '<a :href="typeof to === \'string\' ? to : String(to)"><slot /></a>',
  },
}

const { enableMutateMock, disableMutateMock, updateMutateMock, detailRefetchMock, runsRefetchMock } = vi.hoisted(() => ({
  enableMutateMock: vi.fn(async () => undefined),
  disableMutateMock: vi.fn(async () => undefined),
  updateMutateMock: vi.fn(async () => undefined),
  detailRefetchMock: vi.fn(async () => undefined),
  runsRefetchMock: vi.fn(async () => undefined),
}))

const scheduleDetailState = ref({
  schedule_id: 'schedule-1',
  name: 'Morning smoke',
  app_id: 'app-1',
  plan_ids: ['plan-1'],
  device_ref: 'device-a',
  timezone: 'Asia/Shanghai',
  cron_expr: '0 9 * * 1-5',
  enabled: true,
  next_run_at: '2026-01-01T01:00:00Z',
  last_run_at: '2026-01-01T00:00:00Z',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  queued_run_count: 1,
  active_schedule_run_id: 'schedule-run-1',
  latest_operation_id: 'op-1',
  headless: true,
  fail_fast: false,
  artifact_path: '/tmp/artifacts/nightly',
  assets_root: '/tmp/assets',
  runtime_overrides: {},
  recent_runs: [],
})

const scheduleRunsState = ref({
  schedule_id: 'schedule-1',
  items: [
    {
      schedule_run_id: 'schedule-run-1',
      scheduled_for: '2026-01-01T01:00:00Z',
      status: 'succeeded',
      operation_id: 'op-1',
      error_code: null,
      error_message: null,
      created_at: '2026-01-01T01:00:00Z',
      triggered_at: '2026-01-01T01:00:01Z',
      started_at: '2026-01-01T01:00:02Z',
      finished_at: '2026-01-01T01:05:00Z',
    },
  ],
})
const detailErrorState = ref<unknown>(null)
const runsErrorState = ref<unknown>(null)

vi.mock('vue-router', async () => {
  const actual = await vi.importActual<typeof import('vue-router')>('vue-router')
  return {
    ...actual,
    useRoute: () => ({
      params: {
        scheduleId: 'schedule-1',
      },
    }),
  }
})

vi.mock('@/features/apps/queries/useAppsQuery', () => ({
  useAppsQuery: () => ({
    data: computed(() => [{ app_id: 'app-1', platform: 'android' }]),
    isFetching: ref(false),
    error: ref(null),
  }),
}))

vi.mock('@/features/devices/queries/useDevicesQuery', () => ({
  useDevicesQuery: () => ({
    data: computed(() => [
      { device_ref: 'device-a', display_name: 'Pixel 8', platform: 'android' },
      { device_ref: 'device-b', display_name: 'Pixel 9', platform: 'android' },
    ]),
    isFetching: ref(false),
    error: ref(null),
  }),
}))

vi.mock('@/features/tests/queries/usePlansQuery', () => ({
  usePlansQuery: () => ({
    data: computed(() => ({
      items: [
        { plan_id: 'plan-1', plan_name: 'Settings coverage', case_count: 3, app_id: 'app-1' },
        { plan_id: 'plan-2', plan_name: 'Checkout coverage', case_count: 5, app_id: 'app-1' },
      ],
      total: 2,
      limit: 100,
      offset: 0,
    })),
    isFetching: ref(false),
    error: ref(null),
  }),
}))

vi.mock('../queries/useScheduleDetailQuery', () => ({
  useScheduleDetailQuery: () => ({
    data: computed(() => scheduleDetailState.value),
    isFetching: ref(false),
    error: detailErrorState,
    refetch: detailRefetchMock,
  }),
}))

vi.mock('../queries/useScheduleRunsQuery', () => ({
  useScheduleRunsQuery: () => ({
    data: computed(() => scheduleRunsState.value),
    isFetching: ref(false),
    error: runsErrorState,
    refetch: runsRefetchMock,
  }),
}))

vi.mock('../queries/useScheduleMutations', () => ({
  useScheduleMutations: () => ({
    enableSchedule: {
      isPending: ref(false),
      mutateAsync: enableMutateMock,
    },
    disableSchedule: {
      isPending: ref(false),
      mutateAsync: disableMutateMock,
    },
    updateSchedule: {
      isPending: ref(false),
      mutateAsync: updateMutateMock,
    },
  }),
}))

describe('ScheduleDetailPage', () => {
  beforeEach(() => {
    setLocale('en-US')
    enableMutateMock.mockClear()
    disableMutateMock.mockClear()
    updateMutateMock.mockClear()
    detailRefetchMock.mockClear()
    runsRefetchMock.mockClear()
    detailErrorState.value = null
    runsErrorState.value = null
  })

  it('renders schedule detail and recent history', async () => {
    const wrapper = mount(ScheduleDetailPage, {
      global: {
        plugins: [i18n],
        stubs: globalStubs,
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Morning smoke')
    expect(wrapper.text()).toContain('Back To List')
    expect(wrapper.text()).toContain('plan-1')
    expect(wrapper.text()).toContain('Pixel 8')
    expect(wrapper.text()).not.toContain('Device: device-a')
    expect(wrapper.text()).toContain('Headless Mode')
    expect(wrapper.text()).toContain('Artifact Path')
    expect(wrapper.text()).toContain('/tmp/artifacts/nightly')
    expect(wrapper.text()).toContain('Updated At')
    expect(wrapper.text()).toContain('Queued Runs')
    expect(wrapper.text()).toContain('Recent History')
    expect(wrapper.text()).toContain('Open Run')
    expect(wrapper.text()).toContain('schedule-run-1')
  })

  it('disables the schedule from detail page', async () => {
    const wrapper = mount(ScheduleDetailPage, {
      global: {
        plugins: [i18n],
        stubs: globalStubs,
      },
    })

    await flushPromises()

    await wrapper.findAll('button').find((button) => button.text().includes('Disable'))?.trigger('click')
    await flushPromises()

    expect(disableMutateMock).toHaveBeenCalledWith('schedule-1')
    expect(detailRefetchMock).toHaveBeenCalled()
    expect(runsRefetchMock).toHaveBeenCalled()
  })

  it('enters edit mode, saves full update payload, and refreshes detail', async () => {
    const wrapper = mount(ScheduleDetailPage, {
      global: {
        plugins: [i18n],
        stubs: globalStubs,
      },
    })

    await flushPromises()

    await wrapper.findAll('button').find((button) => button.text().includes('Edit'))?.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Selected Plans')
    expect(wrapper.text()).toContain('Template Editor')
    expect(wrapper.text()).toContain('Asia/Shanghai')

    const textInputs = wrapper.findAll('input[type="text"]')
    await textInputs[0]!.setValue('Updated morning smoke')
    await wrapper.find('input[aria-label="Cron Expression"]').setValue('0 10 * * 1-5')
    await flushPromises()

    const select = wrapper.find('select')
    await select.setValue('device-b')
    await flushPromises()

    await wrapper.findAll('button').find((button) => button.text().includes('Checkout coverage'))?.trigger('click')
    await flushPromises()

    await wrapper.find('input[type="checkbox"]').setValue(false)
    await flushPromises()

    await wrapper.findAll('button').find((button) => button.text() === 'Save')?.trigger('click')
    await flushPromises()

    expect(updateMutateMock).toHaveBeenCalledWith({
      scheduleId: 'schedule-1',
      request: {
        name: 'Updated morning smoke',
        app_id: 'app-1',
        plan_ids: ['plan-1', 'plan-2'],
        device_ref: 'device-b',
        cron_expr: '0 10 * * 1-5',
        enabled: false,
        timezone: 'Asia/Shanghai',
        headless: true,
        fail_fast: false,
        artifact_path: '/tmp/artifacts/nightly',
        assets_root: '/tmp/assets',
        runtime_overrides: {},
      },
    })
    expect(detailRefetchMock).toHaveBeenCalled()
    expect(runsRefetchMock).toHaveBeenCalled()
  })

  it('cancels edit mode without submitting update', async () => {
    const wrapper = mount(ScheduleDetailPage, {
      global: {
        plugins: [i18n],
        stubs: globalStubs,
      },
    })

    await flushPromises()

    await wrapper.findAll('button').find((button) => button.text().includes('Edit'))?.trigger('click')
    await flushPromises()
    await wrapper.findAll('button').find((button) => button.text() === 'Cancel')?.trigger('click')
    await flushPromises()

    expect(updateMutateMock).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Recent History')
  })

  it('keeps detail content visible when runs query fails', async () => {
    runsErrorState.value = new Error('Runs failed')
    const wrapper = mount(ScheduleDetailPage, {
      global: {
        plugins: [i18n],
        stubs: globalStubs,
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Morning smoke')
    expect(wrapper.text()).toContain('Queued Runs')
    expect(wrapper.text()).toContain('Recent History')
    expect(wrapper.text()).toContain('Runs failed')
  })

  it('disables save when cron editor reports a local validation error', async () => {
    const wrapper = mount(ScheduleDetailPage, {
      global: {
        plugins: [i18n],
        stubs: globalStubs,
      },
    })

    await flushPromises()

    await wrapper.findAll('button').find((button) => button.text().includes('Edit'))?.trigger('click')
    await flushPromises()

    await wrapper.find('input[aria-label="Cron Expression"]').setValue('bad cron')
    await flushPromises()

    const saveButton = wrapper.findAll('button').find((button) => button.text() === 'Save')
    expect(saveButton?.attributes('disabled')).toBeDefined()

    await saveButton?.trigger('click')
    await flushPromises()

    expect(updateMutateMock).not.toHaveBeenCalled()
  })
})
