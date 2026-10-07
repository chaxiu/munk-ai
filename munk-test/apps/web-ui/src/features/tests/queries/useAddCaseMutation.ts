import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { useMutation, useQueryClient } from '@tanstack/vue-query'

import { addCase, type CaseUpsertRequest } from '@/shared/api/tests'
import { testsKeys } from './testsKeys'

export function useAddCaseMutation(
  appId: MaybeRefOrGetter<string>,
  planId: MaybeRefOrGetter<string>
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationKey: computed(() => [...testsKeys.planDetail(toValue(appId), toValue(planId)), 'cases', 'add']),
    mutationFn: (request: CaseUpsertRequest) => addCase(toValue(appId), toValue(planId), request),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: testsKeys.planDetail(toValue(appId), toValue(planId)) }),
        queryClient.invalidateQueries({ queryKey: testsKeys.all }),
      ])
    },
  })
}
