import { useMutation, useQueryClient } from '@tanstack/vue-query'

import { createApp, deleteApp, updateApp, type AppUpsertRequest } from '@/shared/api/apps'
import { appsKeys } from './appsKeys'

export function useAppMutations() {
  const queryClient = useQueryClient()

  async function invalidateApps(appId?: string) {
    await queryClient.invalidateQueries({ queryKey: appsKeys.all })
    if (appId) {
      await queryClient.invalidateQueries({ queryKey: appsKeys.detail(appId) })
    }
  }

  return {
    createApp: useMutation({
      mutationKey: ['apps', 'create'],
      mutationFn: (request: AppUpsertRequest) => createApp(request),
      onSuccess: async (result) => {
        await invalidateApps(result.profile.app_id)
      },
    }),
    updateApp: useMutation({
      mutationKey: ['apps', 'update'],
      mutationFn: (input: { appId: string, request: AppUpsertRequest }) => updateApp(input.appId, input.request),
      onSuccess: async (result) => {
        await invalidateApps(result.profile.app_id)
      },
    }),
    deleteApp: useMutation({
      mutationKey: ['apps', 'delete'],
      mutationFn: (appId: string) => deleteApp(appId),
      onSuccess: async (_, appId) => {
        await invalidateApps(appId)
      },
    }),
  }
}
