import { computed, ref, toValue } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { typedViFn } from '@/shared/testing/typedViFn'

import PlanDetailPage from '../pages/PlanDetailPage.vue'
import { LocalApiClientError } from '@/shared/api/client'
import { i18n, setLocale } from '@/shared/i18n'

const confirmMock = typedViFn(() => true)
const detailState = ref({
  app_id: 'demo-app',
  plan_id: 'plan-1',
  plan_name: 'Save flow verification',
  source: 'change_verification',
  version: 'v1.0',
  case_count: 1,
  cases: [
    {
      case_id: 'case-1',
      title: 'Open settings',
      intent: 'Open settings page',
      is_core_case: true,
      runner_goal: 'Open settings',
      start_mode: 'reset',
      start_page_id: 'settings',
    },
  ],
})
const routeParamsState = ref({
  appId: 'demo-app',
  planId: 'plan-1',
})
const pushMock = typedViFn()
const runPlanMock = typedViFn(async () => ({ operation_id: 'op-plan-run-1' }))
const addCaseMock = typedViFn(async () => ({
  app_id: 'demo-app',
  plan_id: 'plan-1',
  plan_source: 'change_verification',
  plan_version: 'v1.0',
  case_id: 'case-2',
  title: 'Verify WiFi',
  intent: 'Verify the WiFi entry is visible',
  preconditions: [],
  expected: [],
  procedure: [],
  is_core_case: false,
  runner_goal: 'Open the WiFi settings screen',
  start_mode: 'reset',
  start_page_id: null,
  max_steps: null,
  max_seconds: null,
}))
const deleteCaseMock = typedViFn(async () => ({
  app_id: 'demo-app',
  plan_id: 'plan-1',
  case_id: 'case-1',
  case_count: 0,
}))
const resetAddCaseMock = typedViFn()
const resetDeleteCaseMock = typedViFn()
const appDetailMapState = ref<Record<string, { profile: { app_id: string, platform: string } }>>({
  'demo-app': {
    profile: {
      app_id: 'demo-app',
      platform: 'ios',
    },
  },
  'manual-app': {
    profile: {
      app_id: 'manual-app',
      platform: 'android',
    },
  },
})
const appDetailErrorMapState = ref<Record<string, unknown>>({})
const appsState = ref([
  {
    app_id: 'manual-app',
    platform: 'android',
    entry_identity: null,
  },
])
const devicesState = ref([
  {
    device_ref: 'sim-1',
    display_name: 'iPhone 16',
    platform: 'ios',
  },
  {
    device_ref: 'emulator-1',
    display_name: 'Pixel 9',
    platform: 'android',
  },
])

vi.mock('vue-router', async () => {
  const actual = await vi.importActual<typeof import('vue-router')>('vue-router')
  return {
    ...actual,
    useRouter: () => ({
      push: pushMock,
    }),
    useRoute: () => ({
      params: routeParamsState.value,
    }),
  }
})

vi.mock('../queries/usePlanDetailQuery', () => ({
  usePlanDetailQuery: () => ({
    data: computed(() => detailState.value),
    isFetching: ref(false),
    error: ref(null),
  }),
}))

vi.mock('@/features/apps/queries/useAppDetailQuery', () => ({
  useAppDetailQuery: (appIdInput: unknown) => ({
    data: computed(() => {
      const appId = toValue(appIdInput as string | null | undefined)
      if (!appId || appDetailErrorMapState.value[appId]) {
        return null
      }
      return appDetailMapState.value[appId] ?? null
    }),
    error: computed(() => {
      const appId = toValue(appIdInput as string | null | undefined)
      if (!appId) {
        return null
      }
      return appDetailErrorMapState.value[appId] ?? null
    }),
    isFetching: ref(false),
  }),
}))

vi.mock('@/features/apps/queries/useAppsQuery', () => ({
  useAppsQuery: () => ({
    data: computed(() => appsState.value),
    error: ref(null),
    isFetching: ref(false),
  }),
}))

vi.mock('@/features/devices/queries/useDevicesQuery', () => ({
  useDevicesQuery: () => ({
    data: computed(() => devicesState.value),
    isFetching: ref(false),
    error: ref(null),
  }),
}))

vi.mock('../queries/useRunPlanMutation', () => ({
  useRunPlanMutation: () => ({
    isPending: ref(false),
    error: ref(null),
    mutateAsync: runPlanMock,
  }),
}))

vi.mock('../queries/useAddCaseMutation', () => ({
  useAddCaseMutation: () => ({
    isPending: ref(false),
    error: ref(null),
    mutateAsync: addCaseMock,
    reset: resetAddCaseMock,
  }),
}))

vi.mock('../queries/useDeleteCaseMutation', () => ({
  useDeleteCaseMutation: () => ({
    isPending: ref(false),
    error: ref(null),
    mutateAsync: deleteCaseMock,
    reset: resetDeleteCaseMock,
  }),
}))

describe('PlanDetailPage', () => {
  beforeEach(() => {
    setLocale('en-US')
    vi.stubGlobal('confirm', confirmMock)
    confirmMock.mockReset()
    confirmMock.mockReturnValue(true)
    pushMock.mockReset()
    runPlanMock.mockClear()
    addCaseMock.mockClear()
    deleteCaseMock.mockClear()
    resetAddCaseMock.mockClear()
    resetDeleteCaseMock.mockClear()
    routeParamsState.value = {
      appId: 'demo-app',
      planId: 'plan-1',
    }
    detailState.value = {
      app_id: 'demo-app',
      plan_id: 'plan-1',
      plan_name: 'Save flow verification',
      source: 'change_verification',
      version: 'v1.0',
      case_count: 1,
      cases: [
        {
          case_id: 'case-1',
          title: 'Open settings',
          intent: 'Open settings page',
          is_core_case: true,
          runner_goal: 'Open settings',
          start_mode: 'reset',
          start_page_id: 'settings',
        },
      ],
    }
    appDetailErrorMapState.value = {}
    appsState.value = [
      {
        app_id: 'manual-app',
        platform: 'android',
        entry_identity: null,
      },
    ]
    devicesState.value = [
      {
        device_ref: 'sim-1',
        display_name: 'iPhone 16',
        platform: 'ios',
      },
      {
        device_ref: 'emulator-1',
        display_name: 'Pixel 9',
        platform: 'android',
      },
    ]
  })

  it('renders plan metadata, case list, and editing actions', async () => {
    const wrapper = mount(PlanDetailPage, {
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

    expect(wrapper.text()).toContain('Save flow verification')
    expect(wrapper.text()).toContain('demo-app / plan-1')
    expect(wrapper.text()).toContain('Change Verification')
    expect(wrapper.text()).toContain('Open settings')
    expect(wrapper.text()).toContain('Start Fresh')
    expect(wrapper.text()).not.toContain('reset')
    expect(wrapper.text()).toContain('Core case')
    expect(wrapper.text()).toContain('Run Plan')
    expect(wrapper.text()).toContain('Add Case')
    expect(wrapper.text()).toContain('Delete')
  })

  it('creates a case from the minimum required fields and routes to case detail', async () => {
    const wrapper = mount(PlanDetailPage, {
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

    await wrapper.findAll('button').find((button) => button.text() === 'Add Case')?.trigger('click')
    await flushPromises()
    wrapper.findComponent({ name: 'CreateCaseModal' }).vm.$emit('update:titleValue', 'Verify WiFi')
    wrapper.findComponent({ name: 'CreateCaseModal' }).vm.$emit('update:intentValue', 'Verify the WiFi entry is visible')
    wrapper.findComponent({ name: 'CreateCaseModal' }).vm.$emit('update:runnerGoalValue', 'Open the WiFi settings screen')
    await flushPromises()
    wrapper.findComponent({ name: 'CreateCaseModal' }).vm.$emit('confirm')
    await flushPromises()

    expect(addCaseMock).toHaveBeenCalledWith({
      case: {
        case_id: 'case-2',
        title: 'Verify WiFi',
        intent: 'Verify the WiFi entry is visible',
        runner_goal: 'Open the WiFi settings screen',
        preconditions: [],
        expected: [],
        procedure: [],
        post_action: [],
        is_core_case: false,
        budget: {
          max_steps: null,
          max_seconds: null,
        },
        start_state: {
          mode: 'reset',
          page_id: null,
        },
        source_metadata: {},
      },
    })
    expect(pushMock).toHaveBeenCalledWith('/tests/plans/demo-app/plan-1/cases/case-2')
  })

  it('deletes the last case and shows empty state', async () => {
    deleteCaseMock.mockImplementationOnce(async () => {
      detailState.value = {
        ...detailState.value,
        case_count: 0,
        cases: [],
      }
      return {
        app_id: 'demo-app',
        plan_id: 'plan-1',
        case_id: 'case-1',
        case_count: 0,
      }
    })

    const wrapper = mount(PlanDetailPage, {
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

    await wrapper.findAll('button').find((button) => button.text() === 'Delete')?.trigger('click')
    await flushPromises()

    expect(confirmMock).toHaveBeenCalled()
    expect(deleteCaseMock).toHaveBeenCalledWith('case-1')
    expect(wrapper.text()).toContain('No cases in this plan')
  })

  it('submits run plan and routes to run detail', async () => {
    const wrapper = mount(PlanDetailPage, {
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

    const selects = wrapper.findAllComponents({ name: 'UiSelect' })
    await selects[0]?.vm.$emit('update:modelValue', 'sim-1')
    await wrapper.findAll('button').find((button) => button.text() === 'Run Plan')?.trigger('click')
    await flushPromises()

    expect(runPlanMock).toHaveBeenCalledWith({
      app_id: 'demo-app',
      plan_id: 'plan-1',
      fail_fast: false,
      headless: false,
      device_ref: 'sim-1',
    })
    expect(pushMock).toHaveBeenCalledWith('/runs/op-plan-run-1')
  })

  it('keeps plan detail visible and allows manual app selection when inferred app is missing', async () => {
    detailState.value = {
      ...detailState.value,
      app_id: 'recording-app',
    }
    routeParamsState.value = {
      appId: 'recording-app',
      planId: 'plan-1',
    }
    appDetailErrorMapState.value = {
      'recording-app': new LocalApiClientError({
        message: 'app not found',
        code: 'app_not_found',
        status: 404,
      }),
    }

    const wrapper = mount(PlanDetailPage, {
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

    expect(wrapper.text()).toContain('Save flow verification')
    expect(wrapper.text()).not.toContain('Failed to load plan detail')
    expect(wrapper.text()).toContain('Pick an app_id from the Apps list before running.')

    const selects = wrapper.findAllComponents({ name: 'UiSelect' })
    await selects[0]?.vm.$emit('update:modelValue', 'manual-app')
    await flushPromises()
    await selects[1]?.vm.$emit('update:modelValue', 'emulator-1')
    await wrapper.findAll('button').find((button) => button.text() === 'Run Plan')?.trigger('click')
    await flushPromises()

    expect(runPlanMock).toHaveBeenCalledWith({
      app_id: 'manual-app',
      plan_id: 'plan-1',
      fail_fast: false,
      headless: false,
      device_ref: 'emulator-1',
    })
  })
})
