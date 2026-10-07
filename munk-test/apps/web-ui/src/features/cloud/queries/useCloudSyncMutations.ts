import { useMutation, useQueryClient } from '@tanstack/vue-query'

import {
  publishCloudSync,
  pullCloudSync,
  pushCloudSync,
  type CloudSyncPublishRequest,
} from '@/shared/api/cloudSync'
import { cloudKeys } from './cloudKeys'

export type CloudSyncMutationInput = {
  force?: boolean
  appId?: string | null
}

export function useCloudSyncPullMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationKey: [...cloudKeys.all, 'sync', 'pull'],
    mutationFn: ({ force = false, appId = null }: CloudSyncMutationInput) => pullCloudSync(force, appId),
    onSuccess: async (_result, variables) => {
      await queryClient.invalidateQueries({ queryKey: cloudKeys.syncStatus(variables.appId) })
      await queryClient.invalidateQueries({ queryKey: cloudKeys.links() })
    },
  })
}

export function useCloudSyncPushMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationKey: [...cloudKeys.all, 'sync', 'push'],
    mutationFn: ({ force = false, appId = null }: CloudSyncMutationInput) => pushCloudSync(force, appId),
    onSuccess: async (_result, variables) => {
      await queryClient.invalidateQueries({ queryKey: cloudKeys.syncStatus(variables.appId) })
      await queryClient.invalidateQueries({ queryKey: cloudKeys.links() })
    },
  })
}

export function useCloudSyncPublishMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationKey: [...cloudKeys.all, 'sync', 'publish'],
    mutationFn: (request: CloudSyncPublishRequest) => publishCloudSync(request),
    onSuccess: async (_result, variables) => {
      await queryClient.invalidateQueries({ queryKey: cloudKeys.links() })
      await queryClient.invalidateQueries({ queryKey: cloudKeys.syncStatus(variables.app_id) })
      await queryClient.invalidateQueries({ queryKey: cloudKeys.apps(variables.workspace_id) })
    },
  })
}
