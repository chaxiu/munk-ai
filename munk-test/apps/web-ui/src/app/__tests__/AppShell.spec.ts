import { flushPromises, mount } from '@vue/test-utils'
import { VueQueryPlugin } from '@tanstack/vue-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { typedViFn } from '@/shared/testing/typedViFn'

import AppShell from '../shell/AppShell.vue'
import { router } from '../router'
import { setLocale, i18n } from '../../shared/i18n'
import { queryClient } from '../../shared/query/queryClient'

vi.mock('@/features/apps/queries/useAppsQuery', () => ({
  useAppsQuery: () => ({
    data: {
      value: [
        {
          app_id: 'demo-app',
          platform: 'android',
          entry_identity: 'com.example.demo',
          introduction_exists: true,
          plan_count: 0,
          case_count: 0,
        },
      ],
    },
    error: { value: null },
    isFetching: { value: false },
  }),
}))

vi.mock('@/features/tests/queries/usePlanImportMutation', () => ({
  usePlanImportMutation: () => ({
    isPending: { value: false },
    mutateAsync: typedViFn(),
  }),
}))

describe('AppShell', () => {
  beforeEach(async () => {
    setLocale('en-US')
    queryClient.clear()
    router.push('/')
    await router.isReady()
  })

  it('renders breadcrumbs and shell controls for the active route', async () => {
    const wrapper = mount(AppShell, {
      global: {
        plugins: [i18n, [VueQueryPlugin, { queryClient }], router],
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Dashboard')
    expect(wrapper.text()).toContain('Recording')
    expect(wrapper.text()).toContain('Schedules')
    expect(wrapper.text()).toContain('Language')
    expect(wrapper.text()).toContain('Theme')
  })

  it('shows dashboard topbar actions', async () => {
    const wrapper = mount(AppShell, {
      global: {
        plugins: [i18n, [VueQueryPlugin, { queryClient }], router],
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Create Test Plan')
    expect(wrapper.text()).toContain('Run Tests')
    await wrapper.find('button.inline-flex.min-h-8.items-center.gap-2.rounded-md.border.border-accent').trigger('click')
    await flushPromises()

    expect(document.body.textContent ?? '').toContain('Import')
    expect(document.body.textContent ?? '').toContain('New')
  })

  it('derives shell actions and document title from route metadata', async () => {
    const wrapper = mount(AppShell, {
      global: {
        plugins: [i18n, [VueQueryPlugin, { queryClient }], router],
      },
    })

    await router.push('/runs')
    await flushPromises()

    expect(wrapper.text()).not.toContain('Create Test Plan')
    expect(document.title).toBe('Runs · Munk Local Web GUI')

    await router.push('/')
    await flushPromises()

    expect(wrapper.text()).toContain('Create Test Plan')
    expect(document.title).toBe('Dashboard · Munk Local Web GUI')
  })

  it('renders the not found page for unknown routes', async () => {
    const wrapper = mount(AppShell, {
      global: {
        plugins: [i18n, [VueQueryPlugin, { queryClient }], router],
      },
    })

    await router.push('/missing-page')
    await flushPromises()

    expect(wrapper.text()).toContain('Page not found')
    expect(wrapper.text()).toContain('Go to dashboard')
    expect(document.title).toBe('Page not found · Munk Local Web GUI')
  })
})
