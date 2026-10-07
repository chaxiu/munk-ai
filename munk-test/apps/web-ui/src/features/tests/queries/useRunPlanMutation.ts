import { useMutation } from '@tanstack/vue-query'

import { submitRunPlan, type RunPlanCliRequest } from '@/shared/api/workflows'

export function useRunPlanMutation() {
  return useMutation({
    mutationFn: (request: RunPlanCliRequest) => submitRunPlan(request, { wait: false, detach: false }),
  })
}
