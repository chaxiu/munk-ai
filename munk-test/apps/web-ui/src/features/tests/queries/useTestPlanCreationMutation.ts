import { useMutation } from '@tanstack/vue-query'

import { submitPlan, type PlanCliRequest } from '@/shared/api/workflows'

export function useTestPlanCreationMutation() {
  return useMutation({
    mutationKey: ['tests', 'create-plan'],
    mutationFn: (request: PlanCliRequest) => submitPlan(request, {
      wait: false,
      detach: false,
    }),
  })
}
