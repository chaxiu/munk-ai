import { useQuery } from '@tanstack/vue-query'
import { computed, type MaybeRefOrGetter, toValue } from 'vue'

import { getCloudSyncStatus } from '@/shared/api/cloudSync'
import { DEFAULT_QUERY_STALE_TIME_MS } from '@/shared/query/defaults'
import { cloudKeys } from './cloudKeys'

export function useCloudSyncStatusQuery(
  enabled: MaybeRefOrGetter<boolean>,
  appId?: MaybeRefOrGetter<string | null | undefined>,
) {
  return useQuery({
    queryKey: computed(() => cloudKeys.syncStatus(toValue(appId))),
    queryFn: () => getCloudSyncStatus(toValue(appId)),
    staleTime: DEFAULT_QUERY_STALE_TIME_MS,
    enabled: computed(() => toValue(enabled)),
    retry: false,
  })
}
