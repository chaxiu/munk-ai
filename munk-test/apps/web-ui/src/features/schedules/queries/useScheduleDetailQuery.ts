import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { useQuery } from '@tanstack/vue-query'

import { getSchedule } from '@/shared/api/schedules'
import { DEFAULT_QUERY_STALE_TIME_MS } from '@/shared/query/defaults'
import { schedulesKeys } from './schedulesKeys'

const SCHEDULE_DETAIL_REFETCH_INTERVAL_MS = 5_000

export function useScheduleDetailQuery(scheduleId: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: computed(() => schedulesKeys.detail(toValue(scheduleId))),
    queryFn: () => getSchedule(toValue(scheduleId)),
    staleTime: DEFAULT_QUERY_STALE_TIME_MS,
    refetchInterval: SCHEDULE_DETAIL_REFETCH_INTERVAL_MS,
  })
}
