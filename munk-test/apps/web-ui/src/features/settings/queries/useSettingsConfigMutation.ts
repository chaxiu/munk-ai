import { useMutation, useQueryClient } from '@tanstack/vue-query'

import { updateSettingsConfig, type SettingsConfigUpsertRequest } from '@/shared/api/settings'
import { settingsKeys } from './settingsKeys'

export function useSettingsConfigMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationKey: ['settings', 'config', 'update'],
    mutationFn: (request: SettingsConfigUpsertRequest) => updateSettingsConfig(request),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: settingsKeys.config() })
    },
  })
}
