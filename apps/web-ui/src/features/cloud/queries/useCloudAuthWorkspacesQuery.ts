import { useQuery } from '@tanstack/vue-query'
import { computed, type MaybeRefOrGetter, toValue } from 'vue'

import { listCloudAuthWorkspaces } from '@/shared/api/cloudAuth'
import { DEFAULT_QUERY_STALE_TIME_MS } from '@/shared/query/defaults'
import { cloudKeys } from './cloudKeys'

export function useCloudAuthWorkspacesQuery(enabled: MaybeRefOrGetter<boolean>) {
  return useQuery({
    queryKey: cloudKeys.workspaces(),
    queryFn: listCloudAuthWorkspaces,
    staleTime: DEFAULT_QUERY_STALE_TIME_MS,
    enabled: computed(() => toValue(enabled)),
  })
}
