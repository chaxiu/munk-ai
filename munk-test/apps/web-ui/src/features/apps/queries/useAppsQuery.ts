import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { useQuery } from '@tanstack/vue-query'

import { listApps } from '@/shared/api/apps'
import { DEFAULT_QUERY_STALE_TIME_MS } from '@/shared/query/defaults'
import { appsKeys } from './appsKeys'

export function useAppsQuery(input: MaybeRefOrGetter<{ platform?: string }>) {
  return useQuery({
    queryKey: computed(() => appsKeys.list(toValue(input))),
    queryFn: () => listApps(toValue(input)),
    staleTime: DEFAULT_QUERY_STALE_TIME_MS,
  })
}
