import { useQuery } from '@tanstack/vue-query'
import { computed, type MaybeRefOrGetter, toValue } from 'vue'

import { listCloudApps } from '@/shared/api/cloudSync'
import { DEFAULT_QUERY_STALE_TIME_MS } from '@/shared/query/defaults'
import { cloudKeys } from './cloudKeys'

export function useCloudAppsQuery(workspaceId: MaybeRefOrGetter<string | null | undefined>) {
  const resolvedWorkspaceId = computed(() => {
    const value = toValue(workspaceId)
    return typeof value === 'string' && value.trim() ? value.trim() : ''
  })

  return useQuery({
    queryKey: computed(() => cloudKeys.apps(resolvedWorkspaceId.value || '_')),
    queryFn: () => listCloudApps(resolvedWorkspaceId.value),
    staleTime: DEFAULT_QUERY_STALE_TIME_MS,
    enabled: computed(() => Boolean(resolvedWorkspaceId.value)),
  })
}
