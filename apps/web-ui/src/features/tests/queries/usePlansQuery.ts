import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { useQuery } from '@tanstack/vue-query'

import { listPlans } from '@/shared/api/tests'
import { DEFAULT_QUERY_STALE_TIME_MS } from '@/shared/query/defaults'
import { testsKeys } from './testsKeys'

export function usePlansQuery(input: MaybeRefOrGetter<{
  appId?: string
  source?: string
  caseCountMode?: 'all' | 'single' | 'multi'
  includeLatestRun?: boolean
  limit?: number
  offset?: number
}>) {
  return useQuery({
    queryKey: computed(() => testsKeys.plans(toValue(input))),
    queryFn: () => listPlans(toValue(input)),
    staleTime: DEFAULT_QUERY_STALE_TIME_MS,
  })
}
