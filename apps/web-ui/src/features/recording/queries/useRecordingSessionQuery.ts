import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { useQuery } from '@tanstack/vue-query'

import { getRecordingSession } from '@/shared/api/recording'
import { DEFAULT_POLL_INTERVAL_MS } from '@/shared/query/defaults'
import { recordingKeys } from './recordingKeys'

export function useRecordingSessionQuery(recordingId: MaybeRefOrGetter<string | null | undefined>) {
  return useQuery({
    queryKey: computed(() => recordingKeys.session(toValue(recordingId) ?? 'unknown')),
    enabled: computed(() => Boolean(toValue(recordingId))),
    queryFn: () => getRecordingSession(toValue(recordingId)!),
    refetchInterval: computed(() => (toValue(recordingId) ? DEFAULT_POLL_INTERVAL_MS : false)),
  })
}
