import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { useQuery } from '@tanstack/vue-query'

import { searchCases } from '@/shared/api/tests'
import { DEFAULT_QUERY_STALE_TIME_MS } from '@/shared/query/defaults'
import { testsKeys } from './testsKeys'

export function useCaseSearchQuery(input: MaybeRefOrGetter<{
  appId?: string
  planId?: string
  caseId?: string
  query?: string
  isCoreCase?: boolean
  startMode?: string
  limit?: number
  offset?: number
}>) {
  return useQuery({
    queryKey: computed(() => testsKeys.caseSearch(toValue(input))),
    queryFn: () => searchCases(toValue(input)),
    staleTime: DEFAULT_QUERY_STALE_TIME_MS,
    enabled: computed(() => {
      const value = toValue(input)
      return Boolean(
        value.caseId?.trim()
        || value.planId?.trim()
        || value.appId?.trim()
        || value.query?.trim()
        || value.isCoreCase !== undefined
        || value.startMode?.trim()
      )
    }),
  })
}
