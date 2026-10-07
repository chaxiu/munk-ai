import { useMutation, useQueryClient } from '@tanstack/vue-query'

import { importPlan } from '@/shared/api/tests'
import { homeKeys } from '@/features/home/queries/homeKeys'
import { testsKeys } from './testsKeys'


export function usePlanImportMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: importPlan,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: homeKeys.summary() }),
        queryClient.invalidateQueries({ queryKey: testsKeys.plans({}) }),
      ])
    },
  })
}
