import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it } from 'vitest'
import { VueQueryPlugin } from '@tanstack/vue-query'

import App from '../../App.vue'
import { router } from '../../app/router'
import { setLocale, i18n } from '../../shared/i18n'
import { queryClient } from '../../shared/query/queryClient'

describe('App entry', () => {
  beforeEach(async () => {
    setLocale('en-US')
    queryClient.clear()
    router.push('/')
    await router.isReady()
  })

  it('renders app shell and dashboard route', async () => {
    const wrapper = mount(App, {
      global: {
        plugins: [
          i18n,
          [VueQueryPlugin, { queryClient }],
          router,
        ],
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Munk AI')
    expect(wrapper.text()).toContain('Dashboard')
    expect(wrapper.text()).toContain('Devices')
    expect(wrapper.text()).toContain('Tests')
  })
})
