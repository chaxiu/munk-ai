import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { useMutation } from '@tanstack/vue-query'

import { rewriteCasePreview, type CaseRewritePreviewRequest } from '@/shared/api/tests'
import { testsKeys } from './testsKeys'

export function useRewriteCasePreviewMutation(
  appId: MaybeRefOrGetter<string>,
  planId: MaybeRefOrGetter<string>,
  caseId: MaybeRefOrGetter<string>
) {
  return useMutation({
    mutationKey: computed(() => [...testsKeys.caseDetail(toValue(appId), toValue(planId), toValue(caseId)), 'rewrite-preview']),
    mutationFn: (request: CaseRewritePreviewRequest) => rewriteCasePreview(toValue(appId), toValue(planId), toValue(caseId), request),
  })
}
