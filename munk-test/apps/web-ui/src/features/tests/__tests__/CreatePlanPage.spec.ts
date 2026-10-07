import { ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { typedViFn } from '@/shared/testing/typedViFn'

import CreatePlanPage from '../pages/CreatePlanPage.vue'
import { i18n, setLocale } from '@/shared/i18n'

const pushMock = typedViFn(async () => undefined)
const mutateAsyncMock = typedViFn()

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: pushMock,
  }),
}))

vi.mock('../queries/useTestPlanCreationMutation', () => ({
  useTestPlanCreationMutation: () => ({
    isPending: ref(false),
    mutateAsync: mutateAsyncMock,
  }),
}))

vi.mock('@/features/apps/queries/useAppsQuery', () => ({
  useAppsQuery: () => ({
    data: ref([
      {
        app_id: 'demo-app',
        platform: 'android',
        entry_identity: 'com.example.demo',
        introduction_exists: true,
        plan_count: 0,
        case_count: 0,
      },
    ]),
    error: ref(null),
    isFetching: ref(false),
  }),
}))

describe('CreatePlanPage', () => {
  beforeEach(() => {
    setLocale('en-US')
    pushMock.mockReset()
    mutateAsyncMock.mockReset()
  })

  it('renders the create form and submits to the progress route', async () => {
    mutateAsyncMock.mockResolvedValue({ operation_id: 'op-123' })

    const wrapper = mount(CreatePlanPage, {
      global: {
        plugins: [i18n],
      },
    })

    await wrapper.find('select').setValue('demo-app')
    const inputs = wrapper.findAll('input')
    await inputs[0]!.setValue('/tmp/requirement.md')
    await inputs[1]!.setValue('/tmp/technical.md')
    await wrapper.find('textarea').setValue('Focus on login edge cases')
    await wrapper.find('.primary-button').trigger('click')
    await flushPromises()

    expect(mutateAsyncMock).toHaveBeenCalledWith({
      app_id: 'demo-app',
      requirement_doc_path: '/tmp/requirement.md',
      technical_doc_path: '/tmp/technical.md',
      user_prompt: 'Focus on login edge cases',
      auto_run: false,
    })
    expect(pushMock).toHaveBeenCalledWith('/tests/create/operations/op-123')
  })

  it('disables submit until required fields are filled', async () => {
    const wrapper = mount(CreatePlanPage, {
      global: {
        plugins: [i18n],
      },
    })

    expect(wrapper.find('.primary-button').attributes('disabled')).toBeDefined()

    await wrapper.find('select').setValue('demo-app')
    const inputs = wrapper.findAll('input')
    await inputs[0]!.setValue('/tmp/requirement.md')
    await flushPromises()

    expect(wrapper.find('.primary-button').attributes('disabled')).toBeUndefined()
  })
})
