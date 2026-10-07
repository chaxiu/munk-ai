import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { useQuery } from '@tanstack/vue-query'

import { getCaseDetail } from '@/shared/api/tests'
import { DEFAULT_QUERY_STALE_TIME_MS } from '@/shared/query/defaults'
import { testsKeys } from './testsKeys'

export function useCaseDetailQuery(
  appId: MaybeRefOrGetter<string>,
  planId: MaybeRefOrGetter<string>,
  caseId: MaybeRefOrGetter<string>
) {
  return useQuery({
    queryKey: computed(() => testsKeys.caseDetail(toValue(appId), toValue(planId), toValue(caseId))),
    queryFn: () => getCaseDetail(toValue(appId), toValue(planId), toValue(caseId)),
    staleTime: DEFAULT_QUERY_STALE_TIME_MS,
  })
}
