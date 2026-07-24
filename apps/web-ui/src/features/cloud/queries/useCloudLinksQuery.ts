import { useQuery } from '@tanstack/vue-query'
import { computed, type MaybeRefOrGetter, toValue } from 'vue'

import { getCloudLinks } from '@/shared/api/cloudSync'
import { DEFAULT_QUERY_STALE_TIME_MS } from '@/shared/query/defaults'
import { cloudKeys } from './cloudKeys'

export function useCloudLinksQuery(enabled: MaybeRefOrGetter<boolean>) {
  return useQuery({
    queryKey: cloudKeys.links(),
    queryFn: getCloudLinks,
    staleTime: DEFAULT_QUERY_STALE_TIME_MS,
    enabled: computed(() => toValue(enabled)),
  })
}
