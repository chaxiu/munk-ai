import { useMutation, useQueryClient } from '@tanstack/vue-query'

import {
  createKnowledgeCard,
  deleteKnowledgeCard,
  updateKnowledgeCard,
  type KnowledgeCardInput,
} from '@/shared/api/knowledge'
import { appsKeys } from './appsKeys'
import { knowledgeKeys } from './knowledgeKeys'

export function useKnowledgeCardMutations() {
  const queryClient = useQueryClient()

  async function invalidate(appId: string, cardId?: string | null) {
    await queryClient.invalidateQueries({ queryKey: knowledgeKeys.all })
    await queryClient.invalidateQueries({ queryKey: appsKeys.detail(appId) })
    await queryClient.invalidateQueries({ queryKey: appsKeys.list() })
    if (cardId) {
      await queryClient.invalidateQueries({ queryKey: knowledgeKeys.cardDetail(appId, cardId) })
    }
  }

  return {
    createCard: useMutation({
      mutationKey: ['apps', 'knowledge', 'cards', 'create'],
      mutationFn: (input: {
        appId: string
        card: KnowledgeCardInput
      }) => createKnowledgeCard(input),
      onSuccess: async (result, input) => {
        await invalidate(input.appId, result.card.card_id)
      },
    }),
    updateCard: useMutation({
      mutationKey: ['apps', 'knowledge', 'cards', 'update'],
      mutationFn: (input: {
        appId: string
        cardId: string
        card: KnowledgeCardInput
      }) => updateKnowledgeCard(input),
      onSuccess: async (result, input) => {
        await invalidate(input.appId, result.card.card_id)
      },
    }),
    deleteCard: useMutation({
      mutationKey: ['apps', 'knowledge', 'cards', 'delete'],
      mutationFn: (input: {
        appId: string
        cardId: string
      }) => deleteKnowledgeCard(input),
      onSuccess: async (_, input) => {
        await invalidate(input.appId, input.cardId)
      },
    }),
  }
}
