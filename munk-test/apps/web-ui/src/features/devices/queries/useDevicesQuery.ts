import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { useQuery } from '@tanstack/vue-query'

import { listDevices } from '@/shared/api/recording'
import { DEFAULT_QUERY_STALE_TIME_MS } from '@/shared/query/defaults'
import { deviceKeys } from './deviceKeys'

export function useDevicesQuery(platform: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: computed(() => deviceKeys.list(toValue(platform))),
    queryFn: () => listDevices(toValue(platform) === 'all' ? undefined : toValue(platform)),
    staleTime: DEFAULT_QUERY_STALE_TIME_MS,
  })
}
