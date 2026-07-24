import { useMutation, useQueryClient } from '@tanstack/vue-query'

import { logoutCloudAuth, startCloudAuthLogin } from '@/shared/api/cloudAuth'
import { cloudKeys } from './cloudKeys'

export function useCloudAuthLoginMutation() {
  return useMutation({
    mutationKey: [...cloudKeys.all, 'login'],
    mutationFn: startCloudAuthLogin,
  })
}

export function useCloudAuthLogoutMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationKey: [...cloudKeys.all, 'logout'],
    mutationFn: logoutCloudAuth,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: cloudKeys.all })
    },
  })
}
