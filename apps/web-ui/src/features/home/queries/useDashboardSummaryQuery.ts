import { useQuery } from '@tanstack/vue-query'

import { getDashboardSummary } from '@/shared/api/dashboard'
import { DEFAULT_QUERY_STALE_TIME_MS } from '@/shared/query/defaults'
import { homeKeys } from './homeKeys'

export function useDashboardSummaryQuery() {
  return useQuery({
    queryKey: homeKeys.summary(),
    queryFn: () => getDashboardSummary(),
    staleTime: DEFAULT_QUERY_STALE_TIME_MS,
  })
}
