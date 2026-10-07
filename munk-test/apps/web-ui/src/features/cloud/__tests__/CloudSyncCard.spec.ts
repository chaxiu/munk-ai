import { computed, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { typedViFn } from '@/shared/testing/typedViFn'

import CloudSyncCard from '../components/CloudSyncCard.vue'
import { LocalApiClientError } from '@/shared/api/client'
import { i18n, setLocale } from '@/shared/i18n'

const pullMutateAsync = typedViFn()
const pushMutateAsync = typedViFn()
const publishMutateAsync = typedViFn()
const putLinkMutateAsync = typedViFn()
const setActiveMutateAsync = typedViFn()
const deleteLinkMutateAsync = typedViFn()

const linksData = ref({
  active_app_id: 'demo-app' as string | null,
  items: [
    {
      workspace_id: 'ws-1',
      app_id: 'demo-app',
      bound_at: '2026-07-09T00:00:00Z',
      workspace_name: 'Demo Workspace',
      role: 'admin',
      dirty: false,
      base_revision: 2,
      last_synced_at: '2026-07-09T01:00:00Z',
      last_action: 'pull' as 'pull' | 'push' | 'force_push' | null,
    },
    {
      workspace_id: 'ws-1',
      app_id: 'other-app',
      bound_at: '2026-07-09T00:10:00Z',
      workspace_name: 'Demo Workspace',
      role: 'member',
      dirty: true,
      base_revision: 1,
      last_synced_at: null,
      last_action: null,
    },
  ],
})

const statusData = ref({
  workspace_id: 'ws-1',
  app_id: 'demo-app',
  revision: 2,
  base_revision: 2,
  role: 'admin',
  can_pull: true,
  can_push: true,
  can_force_push: true,
  dirty: false,
  bound: true,
  last_synced_at: '2026-07-09T01:00:00Z',
  last_action: 'pull' as 'pull' | 'push' | 'force_push' | null,
})

vi.mock('@/features/cloud/lib/useCloudSessionExpiredRecovery', () => ({
  useCloudSessionExpiredRecovery: () => undefined,
}))

vi.mock('@/features/cloud/queries/useCloudLinksQuery', () => ({
  useCloudLinksQuery: () => ({
    data: linksData,
    error: ref(null),
    isFetching: ref(false),
  }),
}))

vi.mock('@/features/cloud/queries/useCloudAuthWorkspacesQuery', () => ({
  useCloudAuthWorkspacesQuery: () => ({
    data: computed(() => ({
      workspaces: [
        { id: 'ws-1', name: 'Demo Workspace', slug: 'demo', role: 'admin' },
      ],
    })),
    error: ref(null),
    isFetching: ref(false),
    isLoading: ref(false),
  }),
}))

vi.mock('@/features/cloud/queries/useCloudAppsQuery', () => ({
  useCloudAppsQuery: () => ({
    data: computed(() => ({
      workspace_id: 'ws-1',
      apps: [
        {
          app_id: 'demo-app',
          app_name: 'Demo',
          platform: 'android',
          revision: 2,
        },
      ],
    })),
    error: ref(null),
    isFetching: ref(false),
  }),
}))

vi.mock('@/features/cloud/queries/useCloudSyncStatusQuery', () => ({
  useCloudSyncStatusQuery: () => ({
    data: statusData,
    error: ref(null),
    isFetching: ref(false),
  }),
}))

vi.mock('@/features/cloud/queries/useCloudLinkMutations', () => ({
  useCloudLinkPutMutation: () => ({
    isPending: ref(false),
    mutateAsync: putLinkMutateAsync,
  }),
  useCloudLinkActiveMutation: () => ({
    isPending: ref(false),
    mutateAsync: setActiveMutateAsync,
  }),
  useCloudLinkDeleteMutation: () => ({
    isPending: ref(false),
    mutateAsync: deleteLinkMutateAsync,
  }),
}))

vi.mock('@/features/apps/queries/useAppsQuery', () => ({
  useAppsQuery: () => ({
    data: computed(() => [
      {
        app_id: 'demo-app',
        app_name: 'Demo',
        platform: 'android',
        entry_identity: 'com.demo',
        introduction_exists: true,
        plan_count: 1,
        case_count: 1,
      },
    ]),
    error: ref(null),
    isFetching: ref(false),
  }),
}))

vi.mock('@/features/cloud/queries/useCloudSyncMutations', () => ({
  useCloudSyncPullMutation: () => ({
    isPending: ref(false),
    mutateAsync: pullMutateAsync,
  }),
  useCloudSyncPushMutation: () => ({
    isPending: ref(false),
    mutateAsync: pushMutateAsync,
  }),
  useCloudSyncPublishMutation: () => ({
    isPending: ref(false),
    mutateAsync: publishMutateAsync,
  }),
}))

function mountCard() {
  return mount(CloudSyncCard, {
    props: { authenticated: true },
    global: {
      plugins: [i18n],
      stubs: {
        Teleport: true,
      },
    },
  })
}

describe('CloudSyncCard', () => {
  beforeEach(() => {
    setLocale('en-US')
    linksData.value = {
      active_app_id: 'demo-app',
      items: [
        {
          workspace_id: 'ws-1',
          app_id: 'demo-app',
          bound_at: '2026-07-09T00:00:00Z',
          workspace_name: 'Demo Workspace',
          role: 'admin',
          dirty: false,
          base_revision: 2,
          last_synced_at: '2026-07-09T01:00:00Z',
          last_action: 'pull',
        },
        {
          workspace_id: 'ws-1',
          app_id: 'other-app',
          bound_at: '2026-07-09T00:10:00Z',
          workspace_name: 'Demo Workspace',
          role: 'member',
          dirty: true,
          base_revision: 1,
          last_synced_at: null,
          last_action: null,
        },
      ],
    }
    statusData.value = {
      workspace_id: 'ws-1',
      app_id: 'demo-app',
      revision: 2,
      base_revision: 2,
      role: 'admin',
      can_pull: true,
      can_push: true,
      can_force_push: true,
      dirty: false,
      bound: true,
      last_synced_at: '2026-07-09T01:00:00Z',
      last_action: 'pull',
    }
    pullMutateAsync.mockReset()
    pushMutateAsync.mockReset()
    publishMutateAsync.mockReset()
    putLinkMutateAsync.mockReset()
    setActiveMutateAsync.mockReset()
    deleteLinkMutateAsync.mockReset()
  })

  it('shows linked apps with pull/push for the current app and keeps link/publish visible', async () => {
    const wrapper = mountCard()
    await flushPromises()

    expect(wrapper.text()).toContain('Linked apps')
    expect(wrapper.text()).toContain('Current')
    expect(wrapper.text()).toContain('Cloud revision')
    expect(wrapper.text()).toContain('demo-app')
    expect(wrapper.text()).toContain('other-app')
    expect(wrapper.text()).toContain('Link from cloud')
    expect(wrapper.text()).toContain('Publish local app')
    expect(wrapper.text()).toContain('Publish to workspace')

    const buttons = wrapper.findAll('button')
    expect(buttons.find((button) => button.text().includes('Pull'))).toBeTruthy()
    expect(buttons.find((button) => button.text().includes('Push'))).toBeTruthy()
    expect(buttons.find((button) => button.text().includes('Set as current'))).toBeTruthy()
  })

  it('sets a linked app as current from the list', async () => {
    const wrapper = mountCard()
    await flushPromises()

    const setCurrentButton = wrapper.findAll('button').find((button) => button.text().includes('Set as current'))
    await setCurrentButton!.trigger('click')
    await flushPromises()

    expect(setActiveMutateAsync).toHaveBeenCalledWith({ app_id: 'other-app' })
  })

  it('publishes a local app from the always-visible publish section', async () => {
    linksData.value = { active_app_id: null, items: [] }
    publishMutateAsync.mockResolvedValueOnce({
      workspace_id: 'ws-1',
      app_id: 'demo-app',
      revision: 1,
      action: 'push',
      forced: false,
      shell_created: true,
    })

    const wrapper = mountCard()
    await flushPromises()

    expect(wrapper.text()).toContain('Link from cloud')
    expect(wrapper.text()).toContain('Publish local app')
    expect(wrapper.text()).toContain('Publish to workspace')

    const selects = wrapper.findAllComponents({ name: 'UiSelect' })
    // Link workspace, link cloud app, publish workspace, publish local app
    expect(selects.length).toBeGreaterThanOrEqual(4)
    await selects[2]?.vm.$emit('update:modelValue', 'ws-1')
    await selects[3]?.vm.$emit('update:modelValue', 'demo-app')
    await flushPromises()

    const publishButton = wrapper.findAll('button').find((button) => button.text().includes('Publish to workspace'))
    expect(publishButton).toBeTruthy()
    expect(publishButton?.attributes('disabled')).toBeUndefined()
    await publishButton!.trigger('click')
    await flushPromises()

    expect(publishMutateAsync).toHaveBeenCalledWith({
      workspace_id: 'ws-1',
      app_id: 'demo-app',
      workspace_name: 'Demo Workspace',
    })
    expect(wrapper.text()).toContain('Published demo-app as revision 1')
  })

  it('renders sync status and disables push when can_push is false', async () => {
    statusData.value = {
      ...statusData.value,
      can_push: false,
      can_force_push: false,
      role: 'member',
    }

    const wrapper = mountCard()
    await flushPromises()

    expect(wrapper.text()).toContain('Cloud revision')
    expect(wrapper.text()).toContain('member')
    expect(wrapper.text()).toContain('Push requires an owner or admin role')

    const buttons = wrapper.findAll('button')
    const pushButton = buttons.find((button) => button.text().includes('Push'))
    expect(pushButton?.attributes('disabled')).toBeDefined()
  })

  it('opens local dirty conflict modal when pull returns 409', async () => {
    pullMutateAsync.mockRejectedValueOnce(new LocalApiClientError({
      message: 'Local sync conflict.',
      code: 'local_sync_conflict',
      status: 409,
      details: {
        base_revision: 1,
        cloud_revision: 3,
      },
    }))

    const wrapper = mountCard()
    await flushPromises()
    const pullButton = wrapper.findAll('button').find((button) => button.text().includes('Pull'))
    await pullButton!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Local changes conflict with cloud')
    expect(wrapper.text()).toContain('Discard local and pull')

    pullMutateAsync.mockResolvedValueOnce({
      workspace_id: 'ws-1',
      app_id: 'demo-app',
      revision: 3,
      plans_written: 1,
      plans_deleted: 0,
      dirty: false,
      forced: true,
    })

    const forcePullButton = wrapper.findAll('button').find((button) => button.text().includes('Discard local and pull'))
    await forcePullButton!.trigger('click')
    await flushPromises()

    expect(pullMutateAsync).toHaveBeenCalledWith({ force: true, appId: 'demo-app' })
    expect(wrapper.text()).toContain('Pulled revision 3')
  })

  it('opens revision conflict modal and supports force push', async () => {
    pushMutateAsync
      .mockRejectedValueOnce(new LocalApiClientError({
        message: 'Sync revision conflict.',
        code: 'sync_revision_conflict',
        status: 409,
        details: {
          expected_revision: 2,
          current_revision: 4,
        },
      }))
      .mockResolvedValueOnce({
        workspace_id: 'ws-1',
        app_id: 'demo-app',
        revision: 5,
        action: 'force_push',
        forced: true,
      })

    const wrapper = mountCard()
    await flushPromises()
    const pushButton = wrapper.findAll('button').find((button) => button.text() === 'Push' || button.text().includes('Push'))
    await pushButton!.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Cloud revision conflict')
    expect(wrapper.text()).toContain('Force push')

    const forcePushButton = wrapper.findAll('button').find((button) => button.text().includes('Force push'))
    await forcePushButton!.trigger('click')
    await flushPromises()

    expect(pushMutateAsync).toHaveBeenLastCalledWith({ force: true, appId: 'demo-app' })
    expect(wrapper.text()).toContain('Pushed revision 5')
  })
})
