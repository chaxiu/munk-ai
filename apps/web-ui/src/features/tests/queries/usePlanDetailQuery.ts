import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { useQuery } from '@tanstack/vue-query'

import { getPlanDetail } from '@/shared/api/tests'
import { DEFAULT_QUERY_STALE_TIME_MS } from '@/shared/query/defaults'
import { testsKeys } from './testsKeys'

export function usePlanDetailQuery(
  appId: MaybeRefOrGetter<string>,
  planId: MaybeRefOrGetter<string>
) {
  return useQuery({
    queryKey: computed(() => testsKeys.planDetail(toValue(appId), toValue(planId))),
    queryFn: () => getPlanDetail(toValue(appId), toValue(planId)),
    staleTime: DEFAULT_QUERY_STALE_TIME_MS,
  })
}
