import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { useQuery } from '@tanstack/vue-query'

import { listOperationArtifactChildren } from '@/shared/api/operations'
import { DEFAULT_POLL_INTERVAL_MS } from '@/shared/query/defaults'
import { isTerminalStatus } from '@/features/runs/lib/runMappers'
import { useRunDetailQuery } from './useRunDetailQuery'
import { runsKeys } from './runsKeys'

export function useRunArtifactChildrenQuery(
  operationId: MaybeRefOrGetter<string>,
  artifactId: MaybeRefOrGetter<string | null>
) {
  const detailQuery = useRunDetailQuery(operationId)

  return useQuery({
    queryKey: computed(() => runsKeys.children(toValue(operationId), toValue(artifactId) ?? 'none')),
    queryFn: () => listOperationArtifactChildren(toValue(operationId), toValue(artifactId) ?? ''),
    enabled: computed(() => Boolean(toValue(operationId)) && Boolean(toValue(artifactId))),
    refetchInterval: () => (isTerminalStatus(detailQuery.data.value?.status) ? false : DEFAULT_POLL_INTERVAL_MS),
  })
}
