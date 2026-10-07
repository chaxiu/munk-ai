import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { useQuery } from '@tanstack/vue-query'

import { getOperationArtifacts } from '@/shared/api/operations'
import { DEFAULT_POLL_INTERVAL_MS } from '@/shared/query/defaults'
import { isTerminalStatus } from '@/features/runs/lib/runMappers'
import { runsKeys } from './runsKeys'

export function useRunArtifactsQuery(operationId: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: computed(() => runsKeys.artifacts(toValue(operationId))),
    queryFn: () => getOperationArtifacts(toValue(operationId)),
    enabled: computed(() => Boolean(toValue(operationId))),
    refetchInterval: (query) => (isTerminalStatus(query.state.data?.status) ? false : DEFAULT_POLL_INTERVAL_MS),
  })
}
