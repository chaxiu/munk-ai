import { useQueryClient } from '@tanstack/vue-query'
import { watch, type MaybeRefOrGetter, toValue } from 'vue'

import { cloudKeys } from '@/features/cloud/queries/cloudKeys'
import { isCloudSessionExpiredError } from '@/features/cloud/lib/sessionExpired'

/**
 * When any cloud query reports ``session_expired``, Host has already cleared the
 * disk session. Refetch the session summary so the UI flips to signed-out.
 */
export function useCloudSessionExpiredRecovery(
  errorSource: MaybeRefOrGetter<unknown>,
  onExpired?: () => void,
): void {
  const queryClient = useQueryClient()

  watch(
    () => toValue(errorSource),
    async (error) => {
      if (!isCloudSessionExpiredError(error)) {
        return
      }
      onExpired?.()
      await queryClient.invalidateQueries({ queryKey: cloudKeys.session() })
      await queryClient.invalidateQueries({ queryKey: cloudKeys.workspaces() })
    },
  )
}
