import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { useMutation, useQueryClient } from '@tanstack/vue-query'

import { replaceCase, type CaseUpsertRequest } from '@/shared/api/tests'
import { testsKeys } from './testsKeys'

export function useReplaceCaseMutation(
  appId: MaybeRefOrGetter<string>,
  planId: MaybeRefOrGetter<string>,
  caseId: MaybeRefOrGetter<string>
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationKey: computed(() => [...testsKeys.caseDetail(toValue(appId), toValue(planId), toValue(caseId)), 'replace']),
    mutationFn: (request: CaseUpsertRequest) => replaceCase(toValue(appId), toValue(planId), toValue(caseId), request),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: testsKeys.caseDetail(toValue(appId), toValue(planId), toValue(caseId)) }),
        queryClient.invalidateQueries({ queryKey: testsKeys.planDetail(toValue(appId), toValue(planId)) }),
        queryClient.invalidateQueries({ queryKey: testsKeys.all }),
      ])
    },
  })
}
