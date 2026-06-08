import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { useQuery } from '@tanstack/vue-query'

import type { OperationSummaryData } from '@/shared/api/operations'
import { listRunsPage } from '@/shared/api/operations'
import { DEFAULT_POLL_INTERVAL_MS, DEFAULT_QUERY_STALE_TIME_MS } from '@/shared/query/defaults'
import { runsKeys } from './runsKeys'

export function hasActiveRuns(items?: Array<Pick<OperationSummaryData, 'status'>> | null): boolean {
  return (items ?? []).some((item) => item.status === 'queued' || item.status === 'running')
}

export function runsRefetchInterval(data?: {
  items?: Array<Pick<OperationSummaryData, 'status'>> | null
  offset?: number
} | null): number | false {
  if ((data?.offset ?? 0) !== 0) {
    return false
  }
  return hasActiveRuns(data?.items) ? DEFAULT_POLL_INTERVAL_MS : false
}

export function useRunsQuery(input: MaybeRefOrGetter<{
  limit?: number
  offset?: number
  status?: 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled'
  kind?: 'plan' | 'run_case' | 'run_plan' | 'run_plans' | 'verify_change' | 'review' | 'record_case'
  deviceRef?: string
  surface?: string
  verificationVerdict?: string
  platform?: string
  query?: string
  runType?: string
}>) {
  return useQuery({
    queryKey: computed(() => runsKeys.list(toValue(input))),
    queryFn: () => listRunsPage(toValue(input)),
    staleTime: DEFAULT_QUERY_STALE_TIME_MS,
    refetchInterval: (query) => runsRefetchInterval(query.state.data),
  })
}
