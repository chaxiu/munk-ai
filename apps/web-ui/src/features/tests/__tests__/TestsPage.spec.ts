import { computed, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { typedViFn } from '@/shared/testing/typedViFn'

import TestsPage from '../pages/TestsPage.vue'
import { i18n, setLocale } from '@/shared/i18n'

type MockPlanItem = {
  app_id: string
  plan_id: string
  plan_name: string
  source: string
  version: string
  case_count: number
  updated_at: string
  latest_run?: {
    operation_id: string
    status: string
    verification_verdict?: string | null
    created_at: string
    started_at?: string | null
    finished_at?: string | null
  } | null
}

type MockSearchItem = {
  app_id: string
  plan_id: string
  plan_name: string
  case_id: string
  ordinal: number
  title: string
  intent: string
  runner_goal: string
  is_core_case: boolean
  start_mode: string
  start_page_id: string | null
  max_steps: number | null
  max_seconds: number | null
}

const plansState = ref<MockPlanItem[]>([])
const searchState = ref<MockSearchItem[]>([])

function makePlan(index: number): MockPlanItem {
  return {
    app_id: 'demo-app',
    plan_id: `plan-${index}`,
    plan_name: `Plan ${index}`,
    source: index % 2 === 0 ? 'change_verification' : 'pydantic_plan_agent',
    version: 'v1.0',
    case_count: index % 3 === 0 ? 1 : 2,
    updated_at: `2026-01-${String((index % 9) + 1).padStart(2, '0')}T00:00:00Z`,
    latest_run: index === 1
      ? {
          operation_id: 'run-plan-1',
          status: 'succeeded',
          verification_verdict: 'passed',
          created_at: '2026-01-03T00:00:00Z',
          started_at: '2026-01-03T00:00:10Z',
          finished_at: '2026-01-03T00:01:00Z',
        }
      : null,
  }
}

function resetMockState() {
  plansState.value = Array.from({ length: 21 }, (_, index) => makePlan(index + 1))
  searchState.value = [
    {
      app_id: 'demo-app',
      plan_id: 'plan-2',
      plan_name: 'Plan 2',
      case_id: 'case-1',
      ordinal: 0,
      title: 'Open settings',
      intent: 'Open settings page',
      runner_goal: 'Open settings',
      is_core_case: true,
      start_mode: 'reset',
      start_page_id: 'settings',
      max_steps: 20,
      max_seconds: 120,
    },
    {
      app_id: 'demo-app',
      plan_id: 'plan-3',
      plan_name: 'Plan 3',
      case_id: 'case-2',
      ordinal: 1,
      title: 'Toggle wifi',
      intent: 'Toggle wifi in settings',
      runner_goal: 'Toggle wifi',
      is_core_case: false,
      start_mode: 'resume',
      start_page_id: 'settings_wifi',
      max_steps: null,
      max_seconds: null,
    },
  ]
}

vi.mock('../queries/usePlansQuery', () => ({
  usePlansQuery: (input: { value: { appId?: string, source?: string, caseCountMode?: 'all' | 'single' | 'multi', limit?: number, offset?: number } }) => ({
    data: computed(() => {
      const filtered = plansState.value.filter((item) => (
        (!input.value.appId || item.app_id === input.value.appId)
        && (!input.value.source || item.source === input.value.source)
        && (
          input.value.caseCountMode !== 'single'
          || item.case_count === 1
        )
        && (
          input.value.caseCountMode !== 'multi'
          || item.case_count > 1
        )
      ))
      const limit = input.value.limit ?? 20
      const offset = input.value.offset ?? 0
      return {
        items: filtered.slice(offset, offset + limit),
        total: filtered.length,
        limit,
        offset,
      }
    }),
    isFetching: ref(false),
    error: ref(null),
    refetch: typedViFn(async () => ({ data: plansState.value })),
  }),
}))

vi.mock('../queries/useCaseSearchQuery', () => ({
  useCaseSearchQuery: (input: { value: { appId?: string, planId?: string, caseId?: string, query?: string, isCoreCase?: boolean, startMode?: string, limit?: number, offset?: number } }) => ({
    data: computed(() => {
      const normalizedQuery = input.value.query?.trim().toLowerCase()
      const filtered = searchState.value.filter((item) => (
        (!input.value.appId || item.app_id === input.value.appId)
        && (!input.value.planId || item.plan_id === input.value.planId)
        && (!input.value.caseId || item.case_id === input.value.caseId)
        && (input.value.isCoreCase === undefined || item.is_core_case === input.value.isCoreCase)
        && (!input.value.startMode || item.start_mode === input.value.startMode)
        && (!normalizedQuery || [
          item.title,
          item.intent,
          item.runner_goal,
          item.plan_name,
          item.plan_id,
          item.case_id,
        ].some(value => value.toLowerCase().includes(normalizedQuery)))
      ))
      const limit = input.value.limit ?? 20
      const offset = input.value.offset ?? 0
      return {
        items: filtered.slice(offset, offset + limit),
        total: filtered.length,
        limit,
        offset,
      }
    }),
    isFetching: ref(false),
    error: ref(null),
    refetch: typedViFn(async () => ({ data: searchState.value })),
  }),
}))

describe('TestsPage', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-01-03T00:00:00Z'))
    setLocale('en-US')
    resetMockState()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders plans, latest run summary, and paginates results', async () => {
    const wrapper = mount(TestsPage, {
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

    expect(wrapper.text()).toContain('Plans')
    expect(wrapper.text()).toContain('Plan 1')
    expect(wrapper.text()).toContain('demo-app')
    expect(wrapper.text()).not.toContain('plan-1')
    expect(wrapper.text()).toContain('AI Generated')
    expect(wrapper.text()).toContain('Latest Run')
    expect(wrapper.text()).toContain('Status: succeeded')
    expect(wrapper.text()).toContain('Result: Passed')
    expect(wrapper.text()).toContain('Open Run')
    expect(wrapper.text()).toContain('Page 1 / 2, 21 items total')
    expect(wrapper.text()).not.toContain('Plan 21')

    await wrapper.findAll('button').find((button) => button.text() === 'Next')?.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Page 2 / 2, 21 items total')
    expect(wrapper.text()).toContain('Plan 21')
  })

  it('supports case search with business query and structured filters', async () => {
    const wrapper = mount(TestsPage, {
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

    expect(wrapper.text()).toContain('Plans')

    await wrapper.findAll('button').find((button) => button.text() === 'Case Search')?.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Enter search criteria')

    const inputs = wrapper.findAll('input')
    await inputs[0]!.setValue('wifi')
    await flushPromises()

    const selects = wrapper.findAll('select')
    await selects[1]!.setValue('false')
    await selects[2]!.setValue('resume')
    await flushPromises()

    expect(wrapper.text()).toContain('Toggle wifi')
    expect(wrapper.text()).toContain('case-2')
    expect(wrapper.text()).toContain('Continue Current State')
    expect(wrapper.text()).not.toContain('resume')
    expect(wrapper.text()).toContain('Page 1 / 1, 1 items total')
    expect(wrapper.text()).not.toContain('Open settings')
  })

  it('renders empty state when no plans are available', async () => {
    plansState.value = []

    const wrapper = mount(TestsPage, {
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

    expect(wrapper.text()).toContain('No plans yet')
  })
})
