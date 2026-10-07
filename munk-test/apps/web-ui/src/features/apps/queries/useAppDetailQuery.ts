import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { useQuery } from '@tanstack/vue-query'

import { getAppDetail } from '@/shared/api/apps'
import { DEFAULT_QUERY_STALE_TIME_MS } from '@/shared/query/defaults'
import { appsKeys } from './appsKeys'

export function useAppDetailQuery(appId: MaybeRefOrGetter<string | null | undefined>) {
  return useQuery({
    queryKey: computed(() => appsKeys.detail(toValue(appId))),
    queryFn: () => getAppDetail(String(toValue(appId))),
    enabled: computed(() => Boolean(toValue(appId))),
    staleTime: DEFAULT_QUERY_STALE_TIME_MS,
  })
}
