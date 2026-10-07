import { useMutation, useQueryClient } from '@tanstack/vue-query'

import {
  approveKnowledgeCandidate,
  rejectKnowledgeCandidate,
  type KnowledgeCandidateDecisionRequest,
} from '@/shared/api/knowledge'
import { appsKeys } from './appsKeys'
import { knowledgeKeys } from './knowledgeKeys'

export function useKnowledgeCandidateMutations() {
  const queryClient = useQueryClient()

  async function invalidate(appId: string) {
    await queryClient.invalidateQueries({ queryKey: knowledgeKeys.all })
    await queryClient.invalidateQueries({ queryKey: appsKeys.detail(appId) })
    await queryClient.invalidateQueries({ queryKey: appsKeys.list() })
  }

  return {
    approveCandidate: useMutation({
      mutationKey: ['apps', 'knowledge', 'approve'],
      mutationFn: (input: {
        appId: string
        candidateId: string
        request?: KnowledgeCandidateDecisionRequest
      }) => approveKnowledgeCandidate(input),
      onSuccess: async (_, input) => {
        await invalidate(input.appId)
      },
    }),
    rejectCandidate: useMutation({
      mutationKey: ['apps', 'knowledge', 'reject'],
      mutationFn: (input: {
        appId: string
        candidateId: string
        request?: KnowledgeCandidateDecisionRequest
      }) => rejectKnowledgeCandidate(input),
      onSuccess: async (_, input) => {
        await invalidate(input.appId)
      },
    }),
  }
}
