import { computed, ref } from 'vue'
import { describe, expect, it, vi } from 'vitest'

import { useCloudBoundAppMarker } from '../queries/useCloudBoundAppMarker'

const linksData = ref({
  active_app_id: null as string | null,
  items: [] as Array<{
    workspace_id: string
    app_id: string
    bound_at: string
    role?: string | null
    dirty: boolean
    base_revision?: number | null
    last_synced_at?: string | null
    last_action?: 'pull' | 'push' | 'force_push' | null
  }>,
})

vi.mock('@/features/cloud/queries/useCloudLinksQuery', () => ({
  useCloudLinksQuery: () => ({
    data: linksData,
    error: ref(null),
    isFetching: ref(false),
  }),
}))

describe('useCloudBoundAppMarker', () => {
  it('marks any linked app and exposes dirty from the link item', () => {
    linksData.value = {
      active_app_id: 'demo-app',
      items: [
        {
          workspace_id: 'ws-1',
          app_id: 'demo-app',
          bound_at: '2026-07-09T00:00:00Z',
          role: 'member',
          dirty: true,
        },
        {
          workspace_id: 'ws-1',
          app_id: 'other-linked',
          bound_at: '2026-07-09T00:10:00Z',
          role: 'admin',
          dirty: false,
        },
      ],
    }

    const marker = useCloudBoundAppMarker(computed(() => 'demo-app'))
    expect(marker.boundAppId.value).toBe('demo-app')
    expect(marker.isBound.value).toBe(true)
    expect(marker.isDirty.value).toBe(true)
    expect(marker.isBoundApp('demo-app')).toBe(true)
    expect(marker.isBoundApp('other-linked')).toBe(true)
    expect(marker.isDirtyApp('demo-app')).toBe(true)
    expect(marker.isDirtyApp('other-linked')).toBe(false)

    const other = useCloudBoundAppMarker(computed(() => 'other-app'))
    expect(other.isBound.value).toBe(false)
    expect(other.isDirty.value).toBe(false)
  })
})
