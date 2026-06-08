import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { useQuery } from '@tanstack/vue-query'

import { getKnowledgeCard } from '@/shared/api/knowledge'
import { DEFAULT_QUERY_STALE_TIME_MS } from '@/shared/query/defaults'
import { knowledgeKeys } from './knowledgeKeys'

export function useKnowledgeCardDetailQuery(input: MaybeRefOrGetter<{
  appId: string | null | undefined
  cardId: string | null | undefined
}>) {
  return useQuery({
    queryKey: computed(() => knowledgeKeys.cardDetail(toValue(input).appId, toValue(input).cardId)),
    queryFn: () => getKnowledgeCard({
      appId: String(toValue(input).appId),
      cardId: String(toValue(input).cardId),
    }),
    enabled: computed(() => Boolean(toValue(input).appId) && Boolean(toValue(input).cardId)),
    staleTime: DEFAULT_QUERY_STALE_TIME_MS,
  })
}
