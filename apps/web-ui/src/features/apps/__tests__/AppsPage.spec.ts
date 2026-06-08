import { computed, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { typedViFn } from '@/shared/testing/typedViFn'

import AppsPage from '../pages/AppsPage.vue'
import { i18n, setLocale } from '@/shared/i18n'

const pushMock = typedViFn(async () => undefined)
const appsState = ref([
  {
    app_id: 'demo-app',
    app_name: 'Demo App',
    platform: 'android',
    entry_identity: 'com.example.demo',
    introduction_exists: true,
    plan_count: 1,
    case_count: 2,
  },
])
const refetchAppsMock = typedViFn(async () => ({ data: appsState.value }))

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: pushMock,
  }),
}))

vi.mock('@/features/apps/queries/useAppsQuery', () => ({
  useAppsQuery: () => ({
    data: computed(() => appsState.value),
    error: ref(null),
    isFetching: ref(false),
    refetch: refetchAppsMock,
  }),
}))

describe('AppsPage', () => {
  beforeEach(() => {
    setLocale('en-US')
    pushMock.mockReset()
    refetchAppsMock.mockReset()
  })

  it('renders the app list and routes add app to the dedicated create page', async () => {
    const wrapper = mount(AppsPage, {
      global: {
        plugins: [i18n],
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Demo App')
    expect(wrapper.text()).toContain('demo-app')
    expect(wrapper.find('input[placeholder="For example demo-app"]').exists()).toBe(false)

    await wrapper.find('.primary-button').trigger('click')
    await flushPromises()

    expect(pushMock).toHaveBeenCalledWith({ name: 'apps-create' })
  })

  it('routes app items to the dedicated edit page', async () => {
    const wrapper = mount(AppsPage, {
      global: {
        plugins: [i18n],
      },
    })

    const appButton = wrapper.findAll('button').find((button) => button.text().includes('Open App'))
    expect(appButton).toBeDefined()
    await appButton!.trigger('click')
    await flushPromises()

    expect(pushMock).toHaveBeenCalledWith({
      name: 'apps-edit',
      params: { appId: 'demo-app' },
    })
  })
})
