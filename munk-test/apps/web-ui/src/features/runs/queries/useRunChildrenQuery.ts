import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { useQuery } from '@tanstack/vue-query'

import { getOperationChildren } from '@/shared/api/operations'
import { DEFAULT_POLL_INTERVAL_MS } from '@/shared/query/defaults'
import { runsKeys } from './runsKeys'

export function useRunChildrenQuery(operationId: MaybeRefOrGetter<string>, enabled: MaybeRefOrGetter<boolean>) {
  return useQuery({
    queryKey: computed(() => runsKeys.batchChildren(toValue(operationId))),
    queryFn: () => getOperationChildren(toValue(operationId)),
    enabled: computed(() => Boolean(toValue(operationId)) && Boolean(toValue(enabled))),
    refetchInterval: computed(() => (toValue(enabled) ? DEFAULT_POLL_INTERVAL_MS : false)),
  })
}
