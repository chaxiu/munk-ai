import { useQuery } from '@tanstack/vue-query'

import { listOperations } from '@/shared/api/operations'
import { DEFAULT_QUERY_STALE_TIME_MS } from '@/shared/query/defaults'
import { homeKeys } from './homeKeys'

export function useRecentRunsQuery(limit = 8) {
  return useQuery({
    queryKey: [...homeKeys.recentRuns(), limit] as const,
    queryFn: () => listOperations({ limit, surface: 'run_center' }),
    staleTime: DEFAULT_QUERY_STALE_TIME_MS,
  })
}
