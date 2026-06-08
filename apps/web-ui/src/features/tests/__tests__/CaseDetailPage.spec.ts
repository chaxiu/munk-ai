import { computed, ref, toValue } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import CaseDetailPage from '../pages/CaseDetailPage.vue'
import { i18n, setLocale } from '@/shared/i18n'

const { pushMock, submitRunCaseMock, replaceCaseMock, resetReplaceCaseMock, rewritePreviewMock, resetRewritePreviewMock } = vi.hoisted(() => ({
  pushMock: vi.fn(),
  submitRunCaseMock: vi.fn(async () => ({ operation_id: 'op-1', status: 'queued' })),
  replaceCaseMock: vi.fn(async (payload: unknown) => payload),
  resetReplaceCaseMock: vi.fn(),
  rewritePreviewMock: vi.fn(async () => ({
    case: {
      case_id: 'case-1',
      title: 'Optimized settings flow',
      intent: 'Open the settings page and verify the destination is visible',
      runner_goal: 'Reach the settings screen reliably',
      preconditions: ['User is logged in'],
      expected: ['Settings screen is visible'],
      procedure: ['Launch app', 'Tap settings entry'],
      post_action: ['Return to home'],
      is_core_case: true,
      budget: {
        max_steps: 10,
        max_seconds: 75,
      },
      start_state: {
        mode: 'reset',
        page_id: null,
      },
      source_metadata: {},
    },
    source_prompt: 'make it clearer',
  })),
  resetRewritePreviewMock: vi.fn(),
}))

const caseDetailState = ref({
  app_id: 'demo-app',
  plan_id: 'plan-1',
  plan_source: 'change_verification',
  plan_version: 'v1.0',
  case_id: 'case-1',
  title: 'Open settings',
  intent: 'Open settings page',
  preconditions: ['Logged in'],
  expected: ['Settings is visible'],
  procedure: ['Tap settings'],
  post_action: ['Return to home'],
  is_core_case: true,
  runner_goal: 'Open settings',
  start_mode: 'reset',
  start_page_id: 'settings',
  max_steps: 12,
  max_seconds: 90,
  latest_optimize: {
    operation_id: 'op-opt-1',
    status: 'succeeded',
    created_at: '2026-01-01T00:05:00Z',
    started_at: '2026-01-01T00:05:05Z',
    finished_at: '2026-01-01T00:05:20Z',
    summary: 'Clarified judge expectations and execution hints',
    patched_fields: ['judge_hints', 'interaction_hints'],
    error_message: null,
  },
})

const appDetailMapState = ref({
  'demo-app': {
    profile: {
      app_id: 'demo-app',
      platform: 'android',
      app_introduction_ref: 'introduction.md',
      android: {
        package_name: 'com.example.demo',
        activity_name: null,
      },
      ios: null,
      web: null,
    },
    introduction_markdown: 'Demo app',
    app_target: {
      app_id: 'demo-app',
      platform: 'android',
      android: {
        package_name: 'com.example.demo',
        activity_name: null,
      },
      ios: null,
      web: null,
    },
    plan_count: 1,
    case_count: 2,
  },
  'fallback-app': {
    profile: {
      app_id: 'fallback-app',
      platform: 'android',
      app_introduction_ref: 'introduction.md',
      android: {
        package_name: 'com.example.fallback',
        activity_name: null,
      },
      ios: null,
      web: null,
    },
    introduction_markdown: 'Fallback app',
    app_target: {
      app_id: 'fallback-app',
      platform: 'android',
      android: {
        package_name: 'com.example.fallback',
        activity_name: null,
      },
      ios: null,
      web: null,
    },
    plan_count: 0,
    case_count: 0,
  },
})

const appsState = ref([
  {
    app_id: 'demo-app',
    platform: 'android',
    entry_identity: 'com.example.demo',
    plan_count: 1,
    case_count: 2,
  },
  {
    app_id: 'fallback-app',
    platform: 'android',
    entry_identity: 'com.example.fallback',
    plan_count: 0,
    case_count: 0,
  },
])

const devicesState = ref([
  {
    platform: 'android',
    device_ref: 'emulator-5554',
    display_name: 'Pixel',
    kind: 'emulator',
    availability: 'available',
    is_booted: true,
    raw: {},
  },
])

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
    device_ref: 'emulator-5554',
    created_at: '2026-01-01T00:00:00Z',
  },
])

const routeParamsState = {
  appId: 'demo-app',
  planId: 'plan-1',
  caseId: 'case-1',
}

vi.mock('vue-router', async () => {
  const actual = await vi.importActual<typeof import('vue-router')>('vue-router')
  return {
    ...actual,
    useRoute: () => ({
      params: routeParamsState,
    }),
    useRouter: () => ({
      push: pushMock,
    }),
  }
})

vi.mock('../queries/useCaseDetailQuery', () => ({
  useCaseDetailQuery: () => ({
    data: computed(() => caseDetailState.value),
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

vi.mock('@/features/apps/queries/useAppsQuery', () => ({
  useAppsQuery: () => ({
    data: computed(() => appsState.value),
    isFetching: ref(false),
    error: ref(null),
  }),
}))

vi.mock('@/features/apps/queries/useAppDetailQuery', () => ({
  useAppDetailQuery: (appIdInput: unknown) => ({
    data: computed(() => {
      const appId = toValue(appIdInput as string | null | undefined)
      if (!appId) {
        return null
      }
      return appDetailMapState.value[appId as keyof typeof appDetailMapState.value] ?? null
    }),
    isFetching: ref(false),
    error: ref(null),
  }),
}))

vi.mock('@tanstack/vue-query', async () => {
  const actual = await vi.importActual<typeof import('@tanstack/vue-query')>('@tanstack/vue-query')
  return {
    ...actual,
    useQuery: () => ({
      data: computed(() => recentRunsState.value),
      isFetching: ref(false),
      error: ref(null),
    }),
  }
})

vi.mock('@/shared/api/workflows', () => ({
  submitRunCase: submitRunCaseMock,
}))

vi.mock('../queries/useReplaceCaseMutation', () => ({
  useReplaceCaseMutation: () => ({
    mutateAsync: replaceCaseMock,
    isPending: ref(false),
    error: ref(null),
    reset: resetReplaceCaseMock,
  }),
}))

vi.mock('../queries/useRewriteCasePreviewMutation', () => ({
  useRewriteCasePreviewMutation: () => ({
    mutateAsync: rewritePreviewMock,
    isPending: ref(false),
    error: ref(null),
    reset: resetRewritePreviewMock,
  }),
}))

describe('CaseDetailPage', () => {
  beforeEach(() => {
    setLocale('en-US')
    pushMock.mockReset()
    submitRunCaseMock.mockClear()
    replaceCaseMock.mockClear()
    resetReplaceCaseMock.mockClear()
    rewritePreviewMock.mockClear()
    resetRewritePreviewMock.mockClear()
    routeParamsState.appId = 'demo-app'
    routeParamsState.planId = 'plan-1'
    routeParamsState.caseId = 'case-1'
    caseDetailState.value = {
      app_id: 'demo-app',
      plan_id: 'plan-1',
      plan_source: 'change_verification',
      plan_version: 'v1.0',
      case_id: 'case-1',
      title: 'Open settings',
      intent: 'Open settings page',
      preconditions: ['Logged in'],
      expected: ['Settings is visible'],
      procedure: ['Tap settings'],
      post_action: ['Return to home'],
      is_core_case: true,
      runner_goal: 'Open settings',
      start_mode: 'reset',
      start_page_id: 'settings',
      max_steps: 12,
      max_seconds: 90,
      latest_optimize: {
        operation_id: 'op-opt-1',
        status: 'succeeded',
        created_at: '2026-01-01T00:05:00Z',
        started_at: '2026-01-01T00:05:05Z',
        finished_at: '2026-01-01T00:05:20Z',
        summary: 'Clarified judge expectations and execution hints',
        patched_fields: ['judge_hints', 'interaction_hints'],
        error_message: null,
      },
    }
  })

  it('renders case detail, editor fields, and recent runs', async () => {
    const wrapper = mount(CaseDetailPage, {
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

    expect(wrapper.text()).toContain('Open settings')
    expect(wrapper.findAll('textarea')[1]?.element.value).toContain('Logged in')
    expect(wrapper.findAll('textarea')[4]?.element.value).toContain('Return to home')
    expect(wrapper.text()).toContain('Pixel')
    expect(wrapper.text()).toContain('This case is already bound to an App')
    expect(wrapper.text()).toContain('Save Changes')
    expect(wrapper.text()).toContain('case-1')
    expect(wrapper.text()).toContain('Change Verification')
    expect(wrapper.text()).toContain('Start From')
    expect(wrapper.text()).toContain('Start Fresh')
    expect(wrapper.text()).toContain('AI Optimize')
    expect(wrapper.text()).toContain('Clarified judge expectations and execution hints')
    expect(wrapper.text()).toContain('judge_hints, interaction_hints')
  })

  it('submits a run request with the inferred app and auto-filled package', async () => {
    const wrapper = mount(CaseDetailPage, {
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
    await selects[1]?.vm.$emit('update:modelValue', 'emulator-5554')
    await wrapper.findAll('button').find((button) => button.text() === 'Run Case')?.trigger('click')
    await flushPromises()

    expect(submitRunCaseMock).toHaveBeenCalledWith({
      app_id: 'demo-app',
      plan_id: 'plan-1',
      case_id: 'case-1',
      device_ref: 'emulator-5554',
      package: 'com.example.demo',
    }, { wait: false, detach: false })
    expect(pushMock).toHaveBeenCalledWith('/runs/op-1')
  })

  it('falls back to showing the Android Apps selector when the app cannot be inferred', async () => {
    routeParamsState.appId = ''
    caseDetailState.value.app_id = ''

    const wrapper = mount(CaseDetailPage, {
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

    const optionsText = wrapper.findAll('option').map((option) => option.text())
    expect(wrapper.text()).toContain('The App cannot be inferred from the current case or route')
    expect(optionsText.some((text) => text.includes('fallback-app'))).toBe(true)
    expect(wrapper.findAll('button').find((button) => button.text() === 'Run Case')?.attributes('disabled')).toBeDefined()
    expect(submitRunCaseMock).not.toHaveBeenCalled()
  })

  it('submits a full replace payload from the editor', async () => {
    const wrapper = mount(CaseDetailPage, {
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

    const inputs = wrapper.findAllComponents({ name: 'UiInput' })
    await inputs[0]?.vm.$emit('update:modelValue', 'Open system settings')
    await inputs[1]?.vm.$emit('update:modelValue', 'Reach settings screen')
    await inputs[2]?.vm.$emit('update:modelValue', 'landing')
    await inputs[3]?.vm.$emit('update:modelValue', '15')
    await inputs[4]?.vm.$emit('update:modelValue', '120')
    const textareas = wrapper.findAllComponents({ name: 'UiTextarea' })
    await textareas[0]?.vm.$emit('update:modelValue', 'Open system settings page')
    await textareas[1]?.vm.$emit('update:modelValue', 'Logged in\nOn home page')
    await textareas[2]?.vm.$emit('update:modelValue', 'Settings is visible')
    await textareas[3]?.vm.$emit('update:modelValue', 'Launch app\nTap settings')
    await textareas[4]?.vm.$emit('update:modelValue', 'Return to home\nClear temp state')
    const selects = wrapper.findAllComponents({ name: 'UiSelect' })
    await selects[0]?.vm.$emit('update:modelValue', 'resume')
    await wrapper.find('input[type="checkbox"]').setValue(false)
    await wrapper.findAll('button').find((button) => button.text() === 'Save Changes')?.trigger('click')
    await flushPromises()

    expect(replaceCaseMock).toHaveBeenCalledWith({
      case: {
        case_id: 'case-1',
        title: 'Open system settings',
        intent: 'Open system settings page',
        runner_goal: 'Reach settings screen',
        preconditions: ['Logged in', 'On home page'],
        expected: ['Settings is visible'],
        procedure: ['Launch app', 'Tap settings'],
        post_action: ['Return to home', 'Clear temp state'],
        is_core_case: false,
        budget: {
          max_steps: 15,
          max_seconds: 120,
        },
        start_state: {
          mode: 'resume',
          page_id: 'landing',
        },
      },
    })
  })

  it('generates an AI rewrite preview and applies it to the editor without saving immediately', async () => {
    const wrapper = mount(CaseDetailPage, {
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

    await wrapper.findAll('button').find((button) => button.text() === 'AI Optimize')?.trigger('click')
    await flushPromises()

    const textareas = wrapper.findAllComponents({ name: 'UiTextarea' })
    const promptArea = textareas[textareas.length - 1]
    expect(promptArea).toBeDefined()
    if (!promptArea) {
      throw new Error('prompt textarea not found')
    }
    await promptArea.vm.$emit('update:modelValue', 'Make the case easier to execute and clarify expected results')
    await wrapper.findAll('button').find((button) => button.text() === 'Generate Preview')?.trigger('click')
    await flushPromises()

    expect(rewritePreviewMock).toHaveBeenCalledWith({
      prompt: 'Make the case easier to execute and clarify expected results',
    })
    expect(wrapper.text()).toContain('Optimized settings flow')

    await wrapper.findAll('button').find((button) => button.text() === 'Apply To Editor')?.trigger('click')
    await flushPromises()

    expect(replaceCaseMock).not.toHaveBeenCalled()
    const inputs = wrapper.findAllComponents({ name: 'UiInput' })
    expect(inputs[0]?.props('modelValue')).toBe('Optimized settings flow')
    expect(inputs[1]?.props('modelValue')).toBe('Reach the settings screen reliably')
    expect(wrapper.findAllComponents({ name: 'UiTextarea' })[1]?.props('modelValue')).toBe('User is logged in')
    expect(wrapper.findAllComponents({ name: 'UiTextarea' })[4]?.props('modelValue')).toBe('Return to home')
  })

  it('serializes empty numeric fields to null and validates required fields', async () => {
    const wrapper = mount(CaseDetailPage, {
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

    const inputs = wrapper.findAllComponents({ name: 'UiInput' })
    await inputs[3]?.vm.$emit('update:modelValue', '')
    await inputs[4]?.vm.$emit('update:modelValue', '')
    const textareas = wrapper.findAllComponents({ name: 'UiTextarea' })
    await textareas[0]?.vm.$emit('update:modelValue', '   ')
    await wrapper.findAll('button').find((button) => button.text() === 'Save Changes')?.trigger('click')
    await flushPromises()

    expect(replaceCaseMock).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('intent must not be empty')
  })
})
