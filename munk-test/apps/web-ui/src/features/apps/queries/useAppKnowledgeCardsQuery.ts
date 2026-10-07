import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { useQuery } from '@tanstack/vue-query'

import {
  listKnowledgeCards,
  type KnowledgeCardStatus,
  type KnowledgeCardType,
} from '@/shared/api/knowledge'
import { DEFAULT_QUERY_STALE_TIME_MS } from '@/shared/query/defaults'
import { knowledgeKeys } from './knowledgeKeys'

export function useAppKnowledgeCardsQuery(input: MaybeRefOrGetter<{
  appId: string | null | undefined
  query?: string
  cardType?: KnowledgeCardType | ''
  status?: KnowledgeCardStatus | ''
  limit?: number
  offset?: number
}>) {
  return useQuery({
    queryKey: computed(() => knowledgeKeys.cardsList({
      appId: toValue(input).appId,
      query: toValue(input).query,
      cardType: toValue(input).cardType || undefined,
      status: toValue(input).status || undefined,
      limit: toValue(input).limit,
      offset: toValue(input).offset,
    })),
    queryFn: () => listKnowledgeCards({
      appId: String(toValue(input).appId),
      query: toValue(input).query,
      cardType: toValue(input).cardType || undefined,
      status: toValue(input).status || undefined,
      limit: toValue(input).limit,
      offset: toValue(input).offset,
    }),
    enabled: computed(() => Boolean(toValue(input).appId)),
    staleTime: DEFAULT_QUERY_STALE_TIME_MS,
  })
}
