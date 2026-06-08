import { useMutation, useQueryClient } from '@tanstack/vue-query'

import { type CaseUpdateRequest, updateCaseDetail } from '@/shared/api/tests'
import { testsKeys } from './testsKeys'

export function useCaseUpdateMutation(appId: string, planId: string, caseId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationKey: [...testsKeys.caseDetail(appId, planId, caseId), 'update'],
    mutationFn: (request: CaseUpdateRequest) => updateCaseDetail(appId, planId, caseId, request),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: testsKeys.caseDetail(appId, planId, caseId) }),
        queryClient.invalidateQueries({ queryKey: testsKeys.planDetail(appId, planId) }),
        queryClient.invalidateQueries({ queryKey: testsKeys.all }),
      ])
    },
  })
}
