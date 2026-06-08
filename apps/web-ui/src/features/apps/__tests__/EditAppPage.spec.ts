import { computed, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { typedViFn } from '@/shared/testing/typedViFn'

import EditAppPage from '../pages/EditAppPage.vue'
import { i18n, setLocale } from '@/shared/i18n'

const pushMock = typedViFn(async () => undefined)
const updateAppMock = typedViFn()
const deleteAppMock = typedViFn()
const confirmMock = typedViFn(() => true)

const appDetailState = ref({
  profile: {
    app_id: 'demo-app',
    app_name: 'Demo App',
    platform: 'android',
    app_introduction_ref: 'introduction.md',
    app_knowledge_ref: 'app_knowledge.json',
    android: {
      package_name: 'com.example.demo',
      activity_name: null,
    },
    ios: null,
    web: null,
  },
  introduction_markdown: 'Demo intro',
  app_knowledge_content: '{"首页":{"enter":"打开首页","recognize":"看到首页"}}',
  app_knowledge_exists: true,
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
})

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: pushMock,
  }),
  useRoute: () => ({
    params: {
      appId: 'demo-app',
    },
  }),
}))

vi.mock('@/features/apps/queries/useAppDetailQuery', () => ({
  useAppDetailQuery: () => ({
    data: computed(() => appDetailState.value),
    error: ref(null),
    isFetching: ref(false),
  }),
}))

vi.mock('@/features/apps/queries/useAppMutations', () => ({
  useAppMutations: () => ({
    createApp: {
      isPending: ref(false),
      mutateAsync: typedViFn(),
    },
    updateApp: {
      isPending: ref(false),
      mutateAsync: updateAppMock,
    },
    deleteApp: {
      isPending: ref(false),
      mutateAsync: deleteAppMock,
    },
  }),
}))

describe('EditAppPage', () => {
  beforeEach(() => {
    setLocale('en-US')
    pushMock.mockReset()
    updateAppMock.mockReset()
    deleteAppMock.mockReset()
    confirmMock.mockClear()
    vi.stubGlobal('confirm', confirmMock)
  })

  async function selectKnowledgeFile(wrapper: ReturnType<typeof mount>, content: string, fileName = 'replacement.json') {
    const fileInput = wrapper.find('input[type="file"]')
    const file = new File([content], fileName, { type: 'application/json' })
    Object.defineProperty(fileInput.element, 'files', {
      value: [file],
      configurable: true,
    })
    await fileInput.trigger('change')
    await flushPromises()
  }

  it('loads the existing app and saves updates in the dedicated edit page', async () => {
    const wrapper = mount(EditAppPage, {
      global: {
        plugins: [i18n],
      },
    })

    await flushPromises()

    const textareas = wrapper.findAll('textarea')
    await textareas[0]!.setValue('Updated intro')
    await wrapper.find('.primary-button').trigger('click')
    await flushPromises()

    expect(updateAppMock).toHaveBeenCalledWith({
      appId: 'demo-app',
      request: {
        profile: {
          app_id: 'demo-app',
          app_name: 'Demo App',
          platform: 'android',
          app_introduction_ref: 'introduction.md',
          app_knowledge_ref: 'app_knowledge.json',
          android: {
            package_name: 'com.example.demo',
            activity_name: null,
          },
          ios: null,
          web: null,
        },
        introduction_markdown: 'Updated intro',
        app_knowledge_file_name: null,
        app_knowledge_content: null,
      },
    })
  })

  it('replaces app knowledge only after selecting a new file', async () => {
    const wrapper = mount(EditAppPage, {
      global: {
        plugins: [i18n],
      },
    })

    await flushPromises()
    await selectKnowledgeFile(wrapper, '{"附近":{"enter":"点击附近","recognize":"附近页签高亮"}}')
    await wrapper.find('.primary-button').trigger('click')
    await flushPromises()

    expect(updateAppMock).toHaveBeenCalledWith({
      appId: 'demo-app',
      request: {
        profile: {
          app_id: 'demo-app',
          app_name: 'Demo App',
          platform: 'android',
          app_introduction_ref: 'introduction.md',
          app_knowledge_ref: 'app_knowledge.json',
          android: {
            package_name: 'com.example.demo',
            activity_name: null,
          },
          ios: null,
          web: null,
        },
        introduction_markdown: 'Demo intro',
        app_knowledge_file_name: 'replacement.json',
        app_knowledge_content: '{"附近":{"enter":"点击附近","recognize":"附近页签高亮"}}',
      },
    })
  })

  it('deletes the app and returns to the apps list', async () => {
    const wrapper = mount(EditAppPage, {
      global: {
        plugins: [i18n],
      },
    })

    await flushPromises()
    const deleteButton = wrapper.findAll('button').find((button) => button.text().includes('Delete App'))
    expect(deleteButton).toBeDefined()
    await deleteButton!.trigger('click')
    await flushPromises()

    expect(deleteAppMock).toHaveBeenCalledWith('demo-app')
    expect(pushMock).toHaveBeenCalledWith({ name: 'apps' })
  })
})
