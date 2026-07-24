import { computed, type MaybeRefOrGetter, toValue } from 'vue'

import { useCloudLinksQuery } from '@/features/cloud/queries/useCloudLinksQuery'

/**
 * Shared cloud-linked app marker for asset pages.
 * Any linked app receives a badge; dirty state is stored per link item.
 */
export function useCloudBoundAppMarker(appId?: MaybeRefOrGetter<string | null | undefined>) {
  const linksQuery = useCloudLinksQuery(true)
  const links = computed(() => linksQuery.data.value?.items ?? [])
  const activeAppId = computed(() => linksQuery.data.value?.active_app_id ?? null)
  const boundAppId = activeAppId

  const isBound = computed(() => {
    const current = toValue(appId)
    if (!current) {
      return false
    }
    return links.value.some((item) => item.app_id === current)
  })

  const currentLink = computed(() => {
    const current = toValue(appId)
    if (!current) {
      return null
    }
    return links.value.find((item) => item.app_id === current) ?? null
  })

  const isDirty = computed(() => {
    return Boolean(currentLink.value?.dirty)
  })

  const role = computed(() => {
    return currentLink.value?.role ?? null
  })

  function isBoundApp(candidateAppId: string | null | undefined): boolean {
    if (!candidateAppId) {
      return false
    }
    return links.value.some((item) => item.app_id === candidateAppId)
  }

  function isDirtyApp(candidateAppId: string | null | undefined): boolean {
    if (!candidateAppId) {
      return false
    }
    return Boolean(links.value.find((item) => item.app_id === candidateAppId)?.dirty)
  }

  return {
    linksQuery,
    links,
    activeAppId,
    boundAppId,
    isBound,
    isDirty,
    role,
    isBoundApp,
    isDirtyApp,
  }
}
