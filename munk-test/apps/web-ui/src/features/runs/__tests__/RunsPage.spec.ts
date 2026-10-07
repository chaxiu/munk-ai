import { computed, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { typedViFn } from '@/shared/testing/typedViFn'

import RunsPage from '../pages/RunsPage.vue'
import { i18n, setLocale } from '@/shared/i18n'

const runsState = ref([
  {
    operation_id: 'op-1',
    kind: 'run_case',
    run_type: 'case_run',
    title: 'Open settings',
    target_label: 'demo-app / plan-1 / case-1',
    platform: 'android',
    phase: null,
    source_recording_id: null,
    status: 'failed',
    verification_verdict: 'failed',
    app_id: 'demo-app',
    plan_id: 'plan-1',
    case_id: 'case-1',
    device_ref: 'emulator-5554',
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    operation_id: 'op-2',
    kind: 'run_case',
    run_type: 'replay',
    title: 'Replay flow',
    target_label: 'demo-app / recording-replay:rec-1 / case-1',
    platform: 'android',
    phase: null,
    source_recording_id: 'rec-1',
    status: 'succeeded',
    verification_verdict: 'passed',
    app_id: 'demo-app',
    plan_id: 'recording-replay:rec-1',
    case_id: 'case-1',
    device_ref: 'emulator-5554',
    created_at: '2026-01-02T00:00:00Z',
  },
  {
    operation_id: 'op-3',
    kind: 'run_plans',
    run_type: 'plan_batch_run',
    title: 'Run 2 plans on emulator-5554',
    target_label: 'demo-app / multi-plan batch',
    platform: 'android',
    phase: null,
    source_recording_id: null,
    status: 'running',
    verification_verdict: null,
    app_id: 'demo-app',
    plan_id: null,
    case_id: null,
    device_ref: 'emulator-5554',
    created_at: '2026-01-03T00:00:00Z',
  },
  ...Array.from({ length: 17 }, (_, index) => ({
    operation_id: `op-extra-${index + 4}`,
    kind: 'run_case',
    run_type: 'case_run',
    title: `Extra run ${index + 4}`,
    target_label: `demo-app / plan-1 / case-${index + 4}`,
    platform: 'android',
    phase: null,
    source_recording_id: null,
    status: 'succeeded',
    verification_verdict: 'passed',
    app_id: 'demo-app',
    plan_id: 'plan-1',
    case_id: `case-${index + 4}`,
    device_ref: 'emulator-5554',
    created_at: `2026-01-${String(index + 4).padStart(2, '0')}T00:00:00Z`,
  })),
  {
    operation_id: 'op-page-2',
    kind: 'run_case',
    run_type: 'case_run',
    title: 'Page 2 only run',
    target_label: 'demo-app / plan-2 / case-21',
    platform: 'android',
    phase: null,
    source_recording_id: null,
    status: 'failed',
    verification_verdict: 'failed',
    app_id: 'demo-app',
    plan_id: 'plan-2',
    case_id: 'case-21',
    device_ref: 'emulator-5554',
    created_at: '2026-01-21T00:00:00Z',
  },
])

const refetchMock = typedViFn(async () => ({ data: runsState.value }))
const devicesState = ref([
  {
    device_ref: 'emulator-5554',
    display_name: 'Pixel 8',
    platform: 'android',
  },
])

vi.mock('../queries/useRunsQuery', () => ({
  useRunsQuery: (input: { value: { limit?: number, offset?: number, runType?: string, status?: string, verificationVerdict?: string, platform?: string, deviceRef?: string, query?: string } }) => ({
    data: computed(() => {
      const filters = input.value
      const filtered = runsState.value.filter((item) => (
        (!filters.runType || item.run_type === filters.runType)
        && (!filters.status || item.status === filters.status)
        && (!filters.verificationVerdict || item.verification_verdict === filters.verificationVerdict)
        && (!filters.platform || item.platform === filters.platform)
        && (!filters.deviceRef || item.device_ref === filters.deviceRef)
        && (!filters.query || [item.title, item.target_label, item.operation_id].some((value) => value?.includes(filters.query ?? '')))
      ))
      const limit = filters.limit ?? 20
      const offset = filters.offset ?? 0
      return {
        items: filtered.slice(offset, offset + limit),
        total: filtered.length,
        limit,
        offset,
      }
    }),
    isFetching: ref(false),
    error: ref(null),
    refetch: refetchMock,
  }),
}))

vi.mock('@/features/devices/queries/useDevicesQuery', () => ({
  useDevicesQuery: () => ({
    data: computed(() => devicesState.value),
    isFetching: ref(false),
    error: ref(null),
  }),
}))

describe('RunsPage', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-01-03T00:00:00Z'))
    setLocale('en-US')
    refetchMock.mockClear()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders runs list', async () => {
    const wrapper = mount(RunsPage, {
      global: {
        plugins: [i18n],
        stubs: {
          RouterLink: {
            props: ['to'],
            template: '<a :href="typeof to === \'string\' ? to : \'\'"><slot /></a>',
          },
        },
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Open settings')
    expect(wrapper.text()).toContain('Replay flow')
    expect(wrapper.text()).toContain('Run 2 plans on emulator-5554')
    expect(wrapper.text()).toContain('Multi-Plan Run')
    expect(wrapper.text()).toContain('Replay Run')
    expect(wrapper.text()).toContain('demo-app')
    expect(wrapper.text()).toContain('Pixel 8')
    expect(wrapper.text()).not.toContain('Device: emulator-5554')
    expect(wrapper.text()).not.toContain('demo-app / plan-1 / case-1')
    expect(wrapper.text()).not.toContain('recording-replay:rec-1')
    expect(wrapper.text()).toContain('Page 1 / 2, 21 items total')
    expect(wrapper.text()).toContain('2 days ago')
  })

  it('navigates to next page', async () => {
    const wrapper = mount(RunsPage, {
      global: {
        plugins: [i18n],
        stubs: {
          RouterLink: {
            props: ['to'],
            template: '<a :href="typeof to === \'string\' ? to : \'\'"><slot /></a>',
          },
        },
      },
    })

    await flushPromises()
    const buttons = wrapper.findAll('button')
    const nextButton = buttons.find((item) => item.text() === 'Next')
    if (!nextButton) {
      throw new Error('next button not found')
    }
    await nextButton.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Page 2 / 2, 21 items total')
    expect(wrapper.text()).toContain('Page 2 only run')
    expect(wrapper.text()).not.toContain('Open settings')
  })

  it('resets to first page when filters change', async () => {
    const wrapper = mount(RunsPage, {
      global: {
        plugins: [i18n],
        stubs: {
          RouterLink: {
            props: ['to'],
            template: '<a :href="typeof to === \'string\' ? to : \'\'"><slot /></a>',
          },
        },
      },
    })

    await flushPromises()
    const buttons = wrapper.findAll('button')
    const nextButton = buttons.find((item) => item.text() === 'Next')
    if (!nextButton) {
      throw new Error('next button not found')
    }
    await nextButton.trigger('click')
    await flushPromises()

    const selects = wrapper.findAll('select')
    const runTypeSelect = selects[0]
    if (!runTypeSelect) {
      throw new Error('run type select not found')
    }
    await runTypeSelect.setValue('plan_batch_run')
    await flushPromises()

    expect(wrapper.text()).toContain('Page 1 / 1, 1 items total')
    expect(wrapper.text()).toContain('Run 2 plans on emulator-5554')
    expect(wrapper.text()).not.toContain('Open settings')
    expect(wrapper.text()).not.toContain('Page 2 only run')
  })
})
