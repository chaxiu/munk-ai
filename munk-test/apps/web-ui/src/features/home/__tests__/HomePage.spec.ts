import { computed, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { typedViFn } from '@/shared/testing/typedViFn'

import HomePage from '../pages/HomePage.vue'
import { setLocale, i18n } from '@/shared/i18n'

const summaryState = ref({
  plan_count: 3,
  case_count: 8,
  recent_run_count: 2,
})

const recentRunsState = ref([
  {
    operation_id: 'op-1',
    kind: 'run_case',
    run_type: 'case_run',
    title: 'Open settings',
    target_label: 'demo-app / plan-1 / case-1',
    status: 'failed',
    app_id: 'demo-app',
    plan_id: 'plan-1',
    case_id: 'case-1',
    device_ref: 'sim-1',
    created_at: '2026-01-01T00:00:00Z',
  },
])
const devicesState = ref([
  {
    device_ref: 'sim-1',
    display_name: 'iPhone 16',
    platform: 'ios',
  },
])

const refetchSummary = typedViFn(async () => ({ data: summaryState.value }))
const refetchRuns = typedViFn(async () => ({ data: recentRunsState.value }))

vi.mock('../queries/useDashboardSummaryQuery', () => ({
  useDashboardSummaryQuery: () => ({
    data: computed(() => summaryState.value),
    isFetching: ref(false),
    error: ref(null),
    refetch: refetchSummary,
  }),
}))

vi.mock('../queries/useRecentRunsQuery', () => ({
  useRecentRunsQuery: () => ({
    data: computed(() => recentRunsState.value),
    isFetching: ref(false),
    error: ref(null),
    refetch: refetchRuns,
  }),
}))

vi.mock('@/features/devices/queries/useDevicesQuery', () => ({
  useDevicesQuery: () => ({
    data: computed(() => devicesState.value),
    isFetching: ref(false),
    error: ref(null),
  }),
}))

describe('HomePage', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-01-01T00:10:00Z'))
    setLocale('en-US')
    summaryState.value = {
      plan_count: 3,
      case_count: 8,
      recent_run_count: 2,
    }
    recentRunsState.value = [
      {
        operation_id: 'op-1',
        kind: 'run_case',
        run_type: 'case_run',
        title: 'Open settings',
        target_label: 'demo-app / plan-1 / case-1',
        status: 'failed',
        app_id: 'demo-app',
        plan_id: 'plan-1',
        case_id: 'case-1',
        device_ref: 'sim-1',
        created_at: '2026-01-01T00:00:00Z',
      },
    ]
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders summary cards, recent runs, and quick actions', async () => {
    const wrapper = mount(HomePage, {
      global: {
        plugins: [i18n],
        stubs: {
          RouterLink: {
            template: '<a><slot /></a>',
          },
        },
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Test Plans')
    expect(wrapper.text()).toContain('3')
    expect(wrapper.text()).toContain('Open settings')
    expect(wrapper.text()).toContain('failed')
    expect(wrapper.text()).toContain('Recent Activity')
    expect(wrapper.text()).toContain('Quick Actions')
    expect(wrapper.text()).toContain('Start Recording')
    expect(wrapper.text()).toContain('Open Schedules')
    expect(wrapper.text()).not.toContain('Run Tests')
    expect(wrapper.text()).toContain('demo-app')
    expect(wrapper.text()).toContain('iPhone 16')
    expect(wrapper.text()).not.toContain('sim-1')
    expect(wrapper.text()).not.toContain('demo-app / plan-1 / case-1')
    expect(wrapper.text()).toContain('10 minutes ago')
    expect(wrapper.find('time').attributes('datetime')).toBe('2026-01-01T00:00:00.000Z')
    expect(wrapper.find('time').attributes('title')).toContain('2026')
  })

  it('renders empty state when there are no recent runs', async () => {
    recentRunsState.value = []

    const wrapper = mount(HomePage, {
      global: {
        plugins: [i18n],
        stubs: {
          RouterLink: {
            template: '<a><slot /></a>',
          },
        },
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('No runs yet')
  })
})
