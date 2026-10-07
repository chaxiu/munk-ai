import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { useQuery } from '@tanstack/vue-query'

import { listScheduleRuns } from '@/shared/api/schedules'
import { DEFAULT_QUERY_STALE_TIME_MS } from '@/shared/query/defaults'
import { schedulesKeys } from './schedulesKeys'

const SCHEDULE_RUNS_REFETCH_INTERVAL_MS = 5_000

export function useScheduleRunsQuery(
  scheduleId: MaybeRefOrGetter<string>,
  input: MaybeRefOrGetter<{ limit?: number }>
) {
  return useQuery({
    queryKey: computed(() => schedulesKeys.runs(toValue(scheduleId), toValue(input).limit ?? 20)),
    queryFn: () => listScheduleRuns(toValue(scheduleId), toValue(input)),
    staleTime: DEFAULT_QUERY_STALE_TIME_MS,
    refetchInterval: SCHEDULE_RUNS_REFETCH_INTERVAL_MS,
  })
}
