import { useQuery } from '@tanstack/vue-query'

import { getCloudAuthSession } from '@/shared/api/cloudAuth'
import { DEFAULT_QUERY_STALE_TIME_MS } from '@/shared/query/defaults'
import { cloudKeys } from './cloudKeys'

export function useCloudAuthSessionQuery() {
  return useQuery({
    queryKey: cloudKeys.session(),
    queryFn: getCloudAuthSession,
    staleTime: DEFAULT_QUERY_STALE_TIME_MS,
  })
}
