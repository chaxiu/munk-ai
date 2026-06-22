import { computed, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { typedViFn } from '@/shared/testing/typedViFn'

import AppKnowledgeCandidatesPage from '../pages/AppKnowledgeCandidatesPage.vue'
import { i18n, setLocale } from '@/shared/i18n'

const routeQuery = ref<Record<string, string>>({})
const pushMock = typedViFn(async () => undefined)
const candidatesState = ref({
  items: [
    {
      candidate_id: 'candidate-1',
      app_id: 'demo-app',
      status: 'pending_review',
      submitted_at: '2026-01-01T00:00:00Z',
      candidate: {
        app_id: 'demo-app',
        title: 'Login issue',
        card_type: 'issue',
        confidence: 0.82,
        source: { kind: 'knowledge_agent', note: 'test' },
        payload: {
          symptom: 'login failed',
          trigger: 'tap login',
          workaround: 'retry',
        },
      },
      evidence_refs: [],
    },
  ],
})

vi.mock('vue-router', () => ({
  useRoute: () => ({
    params: { appId: 'demo-app' },
    query: routeQuery.value,
  }),
  useRouter: () => ({
    push: pushMock,
  }),
}))

vi.mock('@/features/apps/queries/useAppDetailQuery', () => ({
  useAppDetailQuery: () => ({
    data: computed(() => ({
      profile: {
        app_id: 'demo-app',
        app_name: 'Demo App',
      },
    })),
    error: ref(null),
    isFetching: ref(false),
  }),
}))

vi.mock('@/features/apps/queries/useAppKnowledgeCandidatesQuery', () => ({
  useAppKnowledgeCandidatesQuery: () => ({
    data: computed(() => candidatesState.value),
    error: ref(null),
    isFetching: ref(false),
    refetch: vi.fn(),
  }),
}))

vi.mock('@/features/apps/queries/useKnowledgeCandidateMutations', () => ({
  useKnowledgeCandidateMutations: () => ({
    approveCandidate: {
      mutateAsync: vi.fn(),
      isPending: ref(false),
      variables: ref(null),
    },
    rejectCandidate: {
      mutateAsync: vi.fn(),
      isPending: ref(false),
      variables: ref(null),
    },
  }),
}))

describe('AppKnowledgeCandidatesPage', () => {
  beforeEach(() => {
    setLocale('en-US')
    routeQuery.value = {}
    candidatesState.value = {
      items: [
        {
          candidate_id: 'candidate-1',
          app_id: 'demo-app',
          status: 'pending_review',
          submitted_at: '2026-01-01T00:00:00Z',
          candidate: {
            app_id: 'demo-app',
            title: 'Login issue',
            card_type: 'issue',
            confidence: 0.82,
            source: { kind: 'knowledge_agent', note: 'test' },
            payload: {
              symptom: 'login failed',
              trigger: 'tap login',
              workaround: 'retry',
            },
          },
          evidence_refs: [],
        },
      ],
    }
    HTMLElement.prototype.scrollIntoView = vi.fn()
  })

  it('highlights the candidate from query parameter', async () => {
    routeQuery.value = { candidate_id: 'candidate-1' }

    const wrapper = mount(AppKnowledgeCandidatesPage, {
      global: {
        plugins: [i18n],
      },
    })

    await flushPromises()

    expect(wrapper.find('.candidate-highlight').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('The requested candidate was not found')
  })

  it('shows not-found hint when query candidate is missing', async () => {
    routeQuery.value = { candidate_id: 'missing-candidate' }

    const wrapper = mount(AppKnowledgeCandidatesPage, {
      global: {
        plugins: [i18n],
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('The requested candidate was not found')
  })
})
