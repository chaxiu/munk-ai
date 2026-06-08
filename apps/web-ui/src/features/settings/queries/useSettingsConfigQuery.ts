import { useQuery } from '@tanstack/vue-query'

import { getSettingsConfig } from '@/shared/api/settings'
import { DEFAULT_QUERY_STALE_TIME_MS } from '@/shared/query/defaults'
import { settingsKeys } from './settingsKeys'

export function useSettingsConfigQuery() {
  return useQuery({
    queryKey: settingsKeys.config(),
    queryFn: getSettingsConfig,
    staleTime: DEFAULT_QUERY_STALE_TIME_MS,
  })
}
