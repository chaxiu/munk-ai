import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { useMutation, useQueryClient } from '@tanstack/vue-query'

import { deleteCase } from '@/shared/api/tests'
import { testsKeys } from './testsKeys'

export function useDeleteCaseMutation(
  appId: MaybeRefOrGetter<string>,
  planId: MaybeRefOrGetter<string>
) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationKey: computed(() => [...testsKeys.planDetail(toValue(appId), toValue(planId)), 'cases', 'delete']),
    mutationFn: (caseId: string) => deleteCase(toValue(appId), toValue(planId), caseId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: testsKeys.planDetail(toValue(appId), toValue(planId)) }),
        queryClient.invalidateQueries({ queryKey: testsKeys.all }),
      ])
    },
  })
}
