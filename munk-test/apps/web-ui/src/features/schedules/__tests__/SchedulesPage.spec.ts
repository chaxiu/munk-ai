import { computed, ref, toValue } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { typedViFn } from '@/shared/testing/typedViFn'

import SchedulesPage from '../pages/SchedulesPage.vue'
import { i18n, setLocale } from '@/shared/i18n'

const routerLinkStub = {
  props: ['to'],
  template: '<a :href="typeof to === \'string\' ? to : String(to)"><slot /></a>',
}

const uiSelectStub = {
  props: ['modelValue', 'options'],
  emits: ['update:modelValue'],
  template: `
    <select
      :value="modelValue"
      @change="$emit('update:modelValue', $event.target.value)"
    >
      <option v-for="option in options" :key="option.value" :value="option.value">
        {{ option.label }}
      </option>
    </select>
  `,
}

const { refetchMock, enableMutateMock, disableMutateMock, scheduleQueryInputs } = vi.hoisted(() => ({
  refetchMock: vi.fn(async () => undefined),
  enableMutateMock: vi.fn(async () => undefined),
  disableMutateMock: vi.fn(async () => undefined),
  scheduleQueryInputs: [] as unknown[],
}))

const schedulesState = ref([
  {
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
  },
  {
    schedule_id: 'schedule-2',
    name: 'Nightly web',
    app_id: 'app-2',
    plan_ids: ['plan-2'],
    device_ref: 'device-b',
    timezone: 'UTC',
    cron_expr: '0 2 * * *',
    enabled: false,
    next_run_at: null,
    last_run_at: '2026-01-01T02:00:00Z',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
])

const appsState = ref([
  { app_id: 'app-1' },
  { app_id: 'app-2' },
])
const devicesState = ref([
  { device_ref: 'device-a', display_name: 'Pixel 8', platform: 'android' },
  { device_ref: 'device-b', display_name: 'Pixel 9', platform: 'android' },
])

vi.mock('../queries/useSchedulesQuery', async () => {
  const vue = await import('vue')

  return {
    useSchedulesQuery: (input: unknown = {}) => {
      scheduleQueryInputs.push(input)
      return {
        data: vue.computed(() => {
          const filters = (vue.toValue(input as never) ?? {}) as {
            enabled?: boolean
            appId?: string
            keyword?: string
            limit?: number
            offset?: number
          }
          const items = schedulesState.value.filter((item) => {
            if (typeof filters.enabled === 'boolean' && item.enabled !== filters.enabled) {
              return false
            }
            if (filters.appId && item.app_id !== filters.appId) {
              return false
            }
            if (filters.keyword) {
              const normalizedKeyword = filters.keyword.trim().toLowerCase()
              const matched = [item.name, item.schedule_id, item.device_ref]
                .map((value) => value?.trim().toLowerCase() ?? '')
                .some((value) => value.includes(normalizedKeyword))
              if (!matched) {
                return false
              }
            }
            return true
          })
          const offset = filters.offset ?? 0
          const limit = filters.limit ?? items.length
          return {
            items: items.slice(offset, offset + limit),
            total: items.length,
            limit,
            offset,
          }
        }),
        isFetching: vue.ref(false),
        error: vue.ref(null),
        refetch: refetchMock,
      }
    },
  }
})

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
  }),
}))

function mountPage() {
  return mount(SchedulesPage, {
    global: {
      plugins: [i18n],
      stubs: {
        RouterLink: routerLinkStub,
        UiSelect: uiSelectStub,
      },
    },
  })
}

describe('SchedulesPage', () => {
  beforeEach(() => {
    setLocale('en-US')
    refetchMock.mockClear()
    enableMutateMock.mockClear()
    disableMutateMock.mockClear()
    scheduleQueryInputs.length = 0
  })

  it('renders schedule list content and filter controls', async () => {
    schedulesState.value = [
      {
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
      },
    ]

    const wrapper = mountPage()

    await flushPromises()

    expect(wrapper.findAll('select')).toHaveLength(2)
    expect(wrapper.find('input[placeholder="Search task name, schedule ID, or device"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Morning smoke')
    expect(wrapper.text()).toContain('schedule-1')
    expect(wrapper.text()).toContain('Pixel 8')
    expect(wrapper.text()).not.toContain('Device: device-a')
    expect(wrapper.text()).toContain('Cron Expression')
    expect(wrapper.text()).toContain('Enabled')
    expect(wrapper.text()).toContain('Open Detail')
  })

  it('filters schedules by keyword matching name', async () => {
    schedulesState.value = [
      {
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
      },
      {
        schedule_id: 'schedule-2',
        name: 'Nightly web',
        app_id: 'app-2',
        plan_ids: ['plan-2'],
        device_ref: 'device-b',
        timezone: 'UTC',
        cron_expr: '0 2 * * *',
        enabled: false,
        next_run_at: null,
        last_run_at: '2026-01-01T02:00:00Z',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    ]

    const wrapper = mountPage()

    await flushPromises()
    await wrapper.find('input[placeholder="Search task name, schedule ID, or device"]').setValue('nightly')
    await flushPromises()

    expect(toValue(scheduleQueryInputs[0] as never)).toMatchObject({ keyword: 'nightly', limit: 20, offset: 0 })
    expect(wrapper.text()).toContain('Nightly web')
    expect(wrapper.text()).not.toContain('Morning smoke')
  })

  it('filters schedules by keyword matching schedule id or device ref', async () => {
    schedulesState.value = [
      {
        schedule_id: 'schedule-alpha',
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
      },
      {
        schedule_id: 'schedule-beta',
        name: 'Nightly web',
        app_id: 'app-2',
        plan_ids: ['plan-2'],
        device_ref: 'device-b',
        timezone: 'UTC',
        cron_expr: '0 2 * * *',
        enabled: false,
        next_run_at: null,
        last_run_at: '2026-01-01T02:00:00Z',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    ]

    const wrapper = mountPage()

    await flushPromises()
    await wrapper.find('input[placeholder="Search task name, schedule ID, or device"]').setValue('device-b')
    await flushPromises()

    expect(toValue(scheduleQueryInputs[0] as never)).toMatchObject({ keyword: 'device-b', limit: 20, offset: 0 })
    expect(wrapper.text()).toContain('Nightly web')
    expect(wrapper.text()).not.toContain('Morning smoke')
  })

  it('renders empty state when there are no schedules', async () => {
    schedulesState.value = []

    const wrapper = mountPage()

    await flushPromises()

    expect(wrapper.text()).toContain('No schedules yet')
  })

  it('filters schedules by app selection', async () => {
    schedulesState.value = [
      {
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
      },
      {
        schedule_id: 'schedule-2',
        name: 'Nightly web',
        app_id: 'app-2',
        plan_ids: ['plan-2'],
        device_ref: 'device-b',
        timezone: 'UTC',
        cron_expr: '0 2 * * *',
        enabled: false,
        next_run_at: null,
        last_run_at: '2026-01-01T02:00:00Z',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    ]

    const wrapper = mountPage()

    await flushPromises()
    await wrapper.findAll('select')[0]?.setValue('app-2')
    await flushPromises()

    expect(toValue(scheduleQueryInputs[0] as never)).toMatchObject({ appId: 'app-2', limit: 20, offset: 0 })
    expect(wrapper.text()).toContain('Nightly web')
    expect(wrapper.text()).not.toContain('Morning smoke')
  })

  it('filters schedules by status selection', async () => {
    schedulesState.value = [
      {
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
      },
      {
        schedule_id: 'schedule-2',
        name: 'Nightly web',
        app_id: 'app-2',
        plan_ids: ['plan-2'],
        device_ref: 'device-b',
        timezone: 'UTC',
        cron_expr: '0 2 * * *',
        enabled: false,
        next_run_at: null,
        last_run_at: '2026-01-01T02:00:00Z',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    ]

    const wrapper = mountPage()

    await flushPromises()
    await wrapper.findAll('select')[1]?.setValue('disabled')
    await flushPromises()

    expect(toValue(scheduleQueryInputs[0] as never)).toMatchObject({ enabled: false, limit: 20, offset: 0 })
    expect(wrapper.text()).toContain('Nightly web')
    expect(wrapper.text()).not.toContain('Morning smoke')
  })

  it('renders filtered empty state when keyword has no match', async () => {
    schedulesState.value = [
      {
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
      },
    ]

    const wrapper = mountPage()

    await flushPromises()
    await wrapper.find('input[placeholder="Search task name, schedule ID, or device"]').setValue('unknown')
    await flushPromises()

    expect(wrapper.text()).toContain('No matching schedules')
    expect(wrapper.text()).not.toContain('No schedules yet')
  })

  it('paginates schedules and resets to the first page when filters change', async () => {
    schedulesState.value = Array.from({ length: 21 }, (_, index) => ({
      schedule_id: `schedule-${index + 1}`,
      name: index === 20 ? 'Nightly web' : `Schedule ${index + 1}`,
      app_id: index === 20 ? 'app-2' : 'app-1',
      plan_ids: [`plan-${index + 1}`],
      device_ref: `device-${index + 1}`,
      timezone: 'UTC',
      cron_expr: '0 2 * * *',
      enabled: index === 20 ? false : true,
      next_run_at: null,
      last_run_at: '2026-01-01T02:00:00Z',
      created_at: `2026-01-${String((index % 9) + 1).padStart(2, '0')}T00:00:00Z`,
      updated_at: `2026-01-${String((index % 9) + 1).padStart(2, '0')}T00:00:00Z`,
    }))

    const wrapper = mountPage()

    await flushPromises()

    expect(wrapper.text()).toContain('Page 1 / 2')
    expect(wrapper.text()).toContain('Schedule 1')
    expect(wrapper.text()).not.toContain('Nightly web')

    await wrapper.findAll('button').find((button) => button.text().includes('Next Page'))?.trigger('click')
    await flushPromises()

    expect(toValue(scheduleQueryInputs[0] as never)).toMatchObject({ limit: 20, offset: 20 })
    expect(wrapper.text()).toContain('Page 2 / 2')
    expect(wrapper.text()).toContain('Nightly web')
    expect(wrapper.text()).not.toContain('Schedule 1')

    await wrapper.find('input[placeholder="Search task name, schedule ID, or device"]').setValue('nightly')
    await flushPromises()

    expect(toValue(scheduleQueryInputs[0] as never)).toMatchObject({ keyword: 'nightly', limit: 20, offset: 0 })
    expect(wrapper.text()).toContain('Nightly web')
    expect(wrapper.text()).not.toContain('Page 2 / 2')
  })

  it('disables an enabled schedule from the list', async () => {
    schedulesState.value = [
      {
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
      },
    ]

    const wrapper = mountPage()

    await flushPromises()

    await wrapper.findAll('button').find((button) => button.text().includes('Disable'))?.trigger('click')
    await flushPromises()

    expect(disableMutateMock).toHaveBeenCalledWith('schedule-1')
    expect(refetchMock).toHaveBeenCalled()
  })
})
