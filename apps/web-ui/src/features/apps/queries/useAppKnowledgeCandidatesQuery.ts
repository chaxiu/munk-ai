import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { useQuery } from '@tanstack/vue-query'

import { listKnowledgeCandidates, type KnowledgeCandidateStatus } from '@/shared/api/knowledge'
import { DEFAULT_QUERY_STALE_TIME_MS } from '@/shared/query/defaults'
import { knowledgeKeys } from './knowledgeKeys'

export function useAppKnowledgeCandidatesQuery(input: MaybeRefOrGetter<{
  appId: string | null | undefined
  status?: KnowledgeCandidateStatus
}>) {
  return useQuery({
    queryKey: computed(() => knowledgeKeys.candidatesList(toValue(input).appId, toValue(input).status)),
    queryFn: () => listKnowledgeCandidates({
      appId: String(toValue(input).appId),
      status: toValue(input).status,
    }),
    enabled: computed(() => Boolean(toValue(input).appId)),
    staleTime: DEFAULT_QUERY_STALE_TIME_MS,
  })
}
