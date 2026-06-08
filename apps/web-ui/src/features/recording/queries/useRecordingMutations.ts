import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { useMutation, useQueryClient } from '@tanstack/vue-query'

import {
  beginRecordingSession,
  createRecordingSession,
  exportRecordingCase,
  recordInteraction,
  replayRecordingCase,
  startRecordingAnalysis,
  stopRecordingSession,
  type ForwardingAckRequest,
} from '@/shared/api/recording'
import type { InteractionPayload } from '@/shared/api/recording.types'
import { recordingKeys } from './recordingKeys'

export function useRecordingMutations(recordingId: MaybeRefOrGetter<string | null | undefined>) {
  const queryClient = useQueryClient()
  const currentRecordingId = computed(() => toValue(recordingId))

  function invalidateCurrentRecording() {
    const value = currentRecordingId.value
    if (!value) {
      return Promise.resolve()
    }
    return Promise.all([
      queryClient.invalidateQueries({ queryKey: recordingKeys.session(value) }),
      queryClient.invalidateQueries({ queryKey: recordingKeys.timeline(value) }),
    ])
  }

  return {
    createSession: useMutation({
      mutationKey: ['recording', 'create'],
      mutationFn: createRecordingSession,
    }),
    beginSession: useMutation({
      mutationKey: ['recording', 'begin'],
      mutationFn: (value: string) => beginRecordingSession(value),
      onSuccess: async (_, value) => {
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: recordingKeys.session(value) }),
          queryClient.invalidateQueries({ queryKey: recordingKeys.timeline(value) }),
        ])
      },
    }),
    stopSession: useMutation({
      mutationKey: ['recording', 'stop'],
      mutationFn: (value: string) => stopRecordingSession(value),
      onSuccess: invalidateCurrentRecording,
    }),
    analyzeSession: useMutation({
      mutationKey: ['recording', 'analyze'],
      mutationFn: (value: string) => startRecordingAnalysis(value),
    }),
    exportCase: useMutation({
      mutationKey: ['recording', 'export'],
      mutationFn: (value: string) => exportRecordingCase(value),
    }),
    replayCase: useMutation({
      mutationKey: ['recording', 'replay'],
      mutationFn: (value: string) => replayRecordingCase(value),
    }),
    recordInteraction: useMutation({
      mutationKey: ['recording', 'interaction'],
      mutationFn: (input: { recordingId: string, interaction: InteractionPayload, ack: ForwardingAckRequest }) =>
        recordInteraction(input.recordingId, input.interaction, input.ack),
      onSuccess: invalidateCurrentRecording,
    }),
  }
}
