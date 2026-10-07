import { ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { typedViFn } from '@/shared/testing/typedViFn'

import CreateAppPage from '../pages/CreateAppPage.vue'
import { i18n, setLocale } from '@/shared/i18n'

const pushMock = typedViFn(async () => undefined)
const createAppMock = typedViFn()

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: pushMock,
  }),
}))

vi.mock('@/features/apps/queries/useAppMutations', () => ({
  useAppMutations: () => ({
    createApp: {
      isPending: ref(false),
      mutateAsync: createAppMock,
    },
    updateApp: {
      isPending: ref(false),
      mutateAsync: typedViFn(),
    },
    deleteApp: {
      isPending: ref(false),
      mutateAsync: typedViFn(),
    },
  }),
}))

describe('CreateAppPage', () => {
  beforeEach(() => {
    setLocale('en-US')
    pushMock.mockReset()
    createAppMock.mockReset()
  })

  it('enables submit without an app knowledge file once required fields are filled', async () => {
    const wrapper = mount(CreateAppPage, {
      global: {
        plugins: [i18n],
      },
    })

    const inputs = wrapper.findAll('input')
    await inputs[0]!.setValue('new-app')
    await inputs[1]!.setValue('New App')
    await inputs[2]!.setValue('com.example.new-app')
    await wrapper.find('textarea').setValue('New app intro')

    expect(wrapper.find('.primary-button').attributes('disabled')).toBeUndefined()
  })

  it('creates an app and returns to the apps list', async () => {
    createAppMock.mockResolvedValue({
      profile: {
        app_id: 'new-app',
        app_name: 'New App',
      },
    })

    const wrapper = mount(CreateAppPage, {
      global: {
        plugins: [i18n],
      },
    })

    const inputs = wrapper.findAll('input')
    await inputs[0]!.setValue('new-app')
    await inputs[1]!.setValue('New App')
    await inputs[2]!.setValue('com.example.new-app')
    await wrapper.find('textarea').setValue('New app intro')
    await wrapper.find('.primary-button').trigger('click')
    await flushPromises()

    expect(createAppMock).toHaveBeenCalledWith({
      profile: {
        app_id: 'new-app',
        app_name: 'New App',
        platform: 'android',
        app_introduction_ref: 'introduction.md',
        app_knowledge_ref: 'app_knowledge.json',
        android: {
          package_name: 'com.example.new-app',
          activity_name: null,
        },
        ios: null,
        web: null,
      },
      introduction_markdown: 'New app intro',
      app_knowledge_file_name: null,
      app_knowledge_content: null,
    })
    expect(pushMock).toHaveBeenCalledWith({ name: 'apps' })
  })
})
