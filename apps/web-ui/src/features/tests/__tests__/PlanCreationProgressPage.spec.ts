import { computed, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { typedViFn } from '@/shared/testing/typedViFn'

import PlanCreationProgressPage from '../pages/PlanCreationProgressPage.vue'
import { i18n, setLocale } from '@/shared/i18n'

const pushMock = typedViFn(async () => undefined)
const refetchMock = typedViFn(async () => undefined)

type MockOperation = {
  operation_id: string
  kind: string
  status: string
  app_id: string | null
  plan_id: string | null
  progress: {
    stage: string
    completed_case_count: number
    target_case_count: number
    case_title?: string
    plan_name?: string
  }
  result: {
    phase: string
    plan_name?: string
    plan_result: {
      plan_name?: string
      case_count: number
      plan_path: string
      snapshot_path: string
    }
  }
  error_code: string | null
  error_message: string | null
}

const operationState = ref<MockOperation>({
  operation_id: 'op-123',
  kind: 'plan',
  status: 'succeeded',
  app_id: 'demo-app',
  plan_id: 'plan-1',
  progress: {
    stage: 'finalizing',
    completed_case_count: 2,
    target_case_count: 2,
    case_title: 'Verify settings save flow',
  },
  result: {
    phase: 'planned',
    plan_result: {
      case_count: 2,
      plan_path: '/tmp/plan.json',
      snapshot_path: '/tmp/snapshot.json',
    },
  },
  error_code: null,
  error_message: null,
})

const eventsState = ref([
  {
    seq: 1,
    timestamp: '2026-01-01T00:00:00Z',
    event_type: 'plan_context_loaded',
    message: 'Context loaded',
    data_json: {},
  },
])

vi.mock('vue-router', () => ({
  useRoute: () => ({
    params: {
      operationId: 'op-123',
    },
  }),
  useRouter: () => ({
    push: pushMock,
  }),
}))

vi.mock('../queries/usePlanCreationProgress', () => ({
  usePlanCreationProgress: () => ({
    operation: computed(() => operationState.value),
    events: computed(() => eventsState.value),
    loading: ref(false),
    error: ref(null),
    polling: ref(false),
    isFinished: ref(true),
    refetch: refetchMock,
  }),
}))

describe('PlanCreationProgressPage', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-01-01T00:10:00Z'))
    setLocale('en-US')
    pushMock.mockReset()
    refetchMock.mockReset()
    operationState.value = {
      operation_id: 'op-123',
      kind: 'plan',
      status: 'succeeded',
      app_id: 'demo-app',
      plan_id: 'plan-1',
      progress: {
        stage: 'finalizing',
        completed_case_count: 2,
        target_case_count: 2,
        case_title: 'Verify settings save flow',
      },
      result: {
        phase: 'planned',
        plan_name: 'Settings coverage',
        plan_result: {
          plan_name: 'Settings coverage',
          case_count: 2,
          plan_path: '/tmp/plan.json',
          snapshot_path: '/tmp/snapshot.json',
        },
      },
      error_code: null,
      error_message: null,
    }
    eventsState.value = [
      {
        seq: 1,
        timestamp: '2026-01-01T00:00:00Z',
        event_type: 'plan_context_loaded',
        message: 'Context loaded',
        data_json: {},
      },
    ]
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders progress details and completes to the plan detail route', async () => {
    const wrapper = mount(PlanCreationProgressPage, {
      global: {
        plugins: [i18n],
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Context loaded')
    expect(wrapper.text()).toContain('Settings coverage')
    expect(wrapper.text()).toContain('plan-1')
    expect(wrapper.text()).toContain('Verify settings save flow')
    expect(wrapper.text()).toContain('/tmp/plan.json')
    expect(wrapper.text()).toContain('10 minutes ago')
    expect(wrapper.find('time').attributes('datetime')).toBe('2026-01-01T00:00:00.000Z')
    expect(wrapper.find('.primary-button').attributes('disabled')).toBeUndefined()

    await wrapper.find('.primary-button').trigger('click')

    expect(pushMock).toHaveBeenCalledWith('/tests/plans/demo-app/plan-1')
  })

  it('renders failure state without enabling complete action', async () => {
    operationState.value = {
      ...operationState.value,
      status: 'failed',
      plan_id: null,
      error_code: 'plan_read_failed',
      error_message: 'failed to build plan',
    }

    const wrapper = mount(PlanCreationProgressPage, {
      global: {
        plugins: [i18n],
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Generation Failed')
    expect(wrapper.text()).toContain('failed to build plan')
    expect(wrapper.find('.primary-button').attributes('disabled')).toBeDefined()
  })
})
