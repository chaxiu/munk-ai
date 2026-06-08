import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { useQuery } from '@tanstack/vue-query'

import { listOperationEvents } from '@/shared/api/operations'
import { DEFAULT_POLL_INTERVAL_MS } from '@/shared/query/defaults'
import { runsKeys } from './runsKeys'

export function useRunEventsQuery(
  operationId: MaybeRefOrGetter<string>,
  pollEnabled: MaybeRefOrGetter<boolean>
) {
  return useQuery({
    queryKey: computed(() => runsKeys.events(toValue(operationId))),
    queryFn: () => listOperationEvents(toValue(operationId), { afterSeq: 0, limit: 200 }),
    enabled: computed(() => Boolean(toValue(operationId))),
    refetchInterval: computed(() => (toValue(pollEnabled) ? DEFAULT_POLL_INTERVAL_MS : false)),
  })
}
