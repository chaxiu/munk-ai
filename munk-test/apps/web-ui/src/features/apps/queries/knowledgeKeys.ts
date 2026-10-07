import type { KnowledgeCandidateStatus, KnowledgeCardStatus, KnowledgeCardType } from '@/shared/api/knowledge'

export const knowledgeKeys = {
  all: ['apps', 'knowledge'] as const,
  candidatesList: (appId: string | null | undefined, status?: KnowledgeCandidateStatus) => [
    ...knowledgeKeys.all,
    'candidates',
    'list',
    appId ?? null,
    status ?? 'all',
  ] as const,
  cardsList: (input: {
    appId: string | null | undefined
    query?: string
    cardType?: KnowledgeCardType
    status?: KnowledgeCardStatus
    limit?: number
    offset?: number
  }) => [
    ...knowledgeKeys.all,
    'cards',
    'list',
    input.appId ?? null,
    input.query ?? '',
    input.cardType ?? 'all',
    input.status ?? 'all',
    input.limit ?? 50,
    input.offset ?? 0,
  ] as const,
  cardDetail: (appId: string | null | undefined, cardId: string | null | undefined) => [
    ...knowledgeKeys.all,
    'cards',
    'detail',
    appId ?? null,
    cardId ?? null,
  ] as const,
}
