import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { useQuery } from '@tanstack/vue-query'

import { listSchedules, type ListSchedulesInput } from '@/shared/api/schedules'
import { DEFAULT_QUERY_STALE_TIME_MS } from '@/shared/query/defaults'
import { schedulesKeys } from './schedulesKeys'

const SCHEDULES_REFETCH_INTERVAL_MS = 5_000

export function useSchedulesQuery(input: MaybeRefOrGetter<ListSchedulesInput> = {}) {
  return useQuery({
    queryKey: computed(() => schedulesKeys.list(toValue(input))),
    queryFn: () => listSchedules(toValue(input)),
    staleTime: DEFAULT_QUERY_STALE_TIME_MS,
    refetchInterval: SCHEDULES_REFETCH_INTERVAL_MS,
  })
}
