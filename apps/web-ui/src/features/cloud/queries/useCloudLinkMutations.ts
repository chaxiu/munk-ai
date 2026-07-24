import { useMutation, useQueryClient } from '@tanstack/vue-query'

import {
  deleteCloudLink,
  putCloudLink,
  putCloudLinkActive,
  type CloudLinkActiveRequest,
  type CloudLinkUpsertRequest,
} from '@/shared/api/cloudSync'
import { cloudKeys } from './cloudKeys'

export function useCloudLinkPutMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationKey: [...cloudKeys.all, 'links', 'put'],
    mutationFn: (body: CloudLinkUpsertRequest) => putCloudLink(body),
    onSuccess: async (_result, variables) => {
      await queryClient.invalidateQueries({ queryKey: cloudKeys.links() })
      await queryClient.invalidateQueries({ queryKey: cloudKeys.syncStatus(variables.app_id) })
    },
  })
}

export function useCloudLinkActiveMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationKey: [...cloudKeys.all, 'links', 'active'],
    mutationFn: (body: CloudLinkActiveRequest) => putCloudLinkActive(body),
    onSuccess: async (_result, variables) => {
      await queryClient.invalidateQueries({ queryKey: cloudKeys.links() })
      await queryClient.invalidateQueries({ queryKey: cloudKeys.syncStatus(variables.app_id) })
    },
  })
}

export function useCloudLinkDeleteMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationKey: [...cloudKeys.all, 'links', 'delete'],
    mutationFn: (appId: string) => deleteCloudLink(appId),
    onSuccess: async (_result, appId) => {
      await queryClient.invalidateQueries({ queryKey: cloudKeys.links() })
      await queryClient.invalidateQueries({ queryKey: cloudKeys.syncStatus(appId) })
    },
  })
}
