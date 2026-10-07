import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { getRecordingAnalysis, type ForwardingAckRequest, type RecordingAnalysisResult, type RecordingBridgeInfo, type RecordingCaseExport, type RecordingReplayResult } from '@/shared/api/recording'
import type { InteractionPayload } from '@/shared/api/recording.types'
import { useRecordingAnalysisProgress } from '@/features/recording/queries/useRecordingAnalysisProgress'
import { useRecordingMutations } from '@/features/recording/queries/useRecordingMutations'
import { useRecordingSessionQuery } from '@/features/recording/queries/useRecordingSessionQuery'
import { useRecordingTimelineQuery } from '@/features/recording/queries/useRecordingTimelineQuery'
import { toUserMessage } from '@/features/recording/lib/toUserMessage'

export function useRecordingWorkspaceController() {
  const { t } = useI18n()

  const recordingId = ref<string | null>(null)
  const analysisOperationId = ref<string | null>(null)
  const analysisModalOpen = ref(false)
  const bridge = ref<RecordingBridgeInfo | null>(null)
  const analysis = ref<RecordingAnalysisResult | null>(null)
  const exportedCase = ref<RecordingCaseExport | null>(null)
  const replayResult = ref<RecordingReplayResult | null>(null)
  const errorMessage = ref<string | null>(null)
  const successMessage = ref<string | null>(null)

  const sessionQuery = useRecordingSessionQuery(recordingId)
  const timelineQuery = useRecordingTimelineQuery(recordingId)
  const analysisProgress = useRecordingAnalysisProgress(analysisOperationId)
  const mutations = useRecordingMutations(recordingId)

  const session = computed(() => sessionQuery.data.value?.session ?? null)
  const events = computed(() => sessionQuery.data.value?.events ?? [])
  const timeline = computed(() => timelineQuery.data.value?.timeline ?? sessionQuery.data.value?.timeline ?? [])
  const analysisOperation = computed(() => analysisProgress.operation.value)
  const analysisEvents = computed(() => analysisProgress.events.value)
  const analysisProgressError = computed(() =>
    analysisProgress.error.value ? toUserMessage(analysisProgress.error.value) : null
  )
  const analysisOperationRunning = computed(() =>
    Boolean(analysisOperationId.value) && !analysisProgress.isFinished()
  )
  const loading = computed(() =>
    sessionQuery.isFetching.value
    || timelineQuery.isFetching.value
    || mutations.createSession.isPending.value
    || mutations.beginSession.isPending.value
    || mutations.stopSession.isPending.value
    || mutations.analyzeSession.isPending.value
    || analysisOperationRunning.value
    || mutations.exportCase.isPending.value
    || mutations.replayCase.isPending.value
    || mutations.recordInteraction.isPending.value
  )

  function resetMessages(): void {
    errorMessage.value = null
    successMessage.value = null
  }

  async function refreshSession() {
    await Promise.all([
      sessionQuery.refetch(),
      timelineQuery.refetch(),
    ])
  }

  async function createSession(input: {
    appId: string
    entryIdentity: string
    deviceRef?: string
  }) {
    resetMessages()
    try {
      const response = await mutations.createSession.mutateAsync(input)
      recordingId.value = response.session.recording_id
      bridge.value = null
      analysis.value = null
      exportedCase.value = null
      replayResult.value = null
      successMessage.value = t('recording.sessionCreated', { id: response.session.recording_id })
    } catch (error) {
      errorMessage.value = toUserMessage(error)
    }
  }

  async function beginSession() {
    if (!recordingId.value) {
      return
    }
    resetMessages()
    try {
      const response = await mutations.beginSession.mutateAsync(recordingId.value)
      bridge.value = response.bridge
      successMessage.value = t('recording.sessionStarted')
      await refreshSession()
    } catch (error) {
      errorMessage.value = toUserMessage(error)
    }
  }

  async function stopSession() {
    if (!recordingId.value) {
      return
    }
    resetMessages()
    try {
      await mutations.stopSession.mutateAsync(recordingId.value)
      successMessage.value = t('recording.sessionStopped')
      await refreshSession()
    } catch (error) {
      errorMessage.value = toUserMessage(error)
    }
  }

  async function analyzeSession() {
    if (!recordingId.value) {
      return
    }
    resetMessages()
    try {
      const response = await mutations.analyzeSession.mutateAsync(recordingId.value)
      analysisOperationId.value = response.operation_id
      analysisModalOpen.value = true
      successMessage.value = t('recording.analysisQueued')
    } catch (error) {
      errorMessage.value = toUserMessage(error)
    }
  }

  async function exportCase() {
    if (!recordingId.value) {
      return
    }
    resetMessages()
    try {
      const response = await mutations.exportCase.mutateAsync(recordingId.value)
      analysis.value = response.analysis
      exportedCase.value = response.case
      successMessage.value = t('recording.caseExported', { id: response.case.case_id })
    } catch (error) {
      errorMessage.value = toUserMessage(error)
    }
  }

  async function replayCase() {
    if (!recordingId.value) {
      return
    }
    resetMessages()
    try {
      const response = await mutations.replayCase.mutateAsync(recordingId.value)
      replayResult.value = response.replay
      successMessage.value = t('recording.caseReplayed', { verdict: response.replay.verdict })
    } catch (error) {
      errorMessage.value = toUserMessage(error)
    }
  }

  function closeAnalysisModal() {
    analysisModalOpen.value = false
  }

  async function handleAnalysisExport() {
    closeAnalysisModal()
    await exportCase()
  }

  async function handleInteractionForwarded(payload: {
    interaction: InteractionPayload
    ack: ForwardingAckRequest
  }) {
    if (!recordingId.value) {
      return
    }
    try {
      await mutations.recordInteraction.mutateAsync({
        recordingId: recordingId.value,
        interaction: payload.interaction,
        ack: payload.ack,
      })
      successMessage.value = t('recording.interactionRecorded', { kind: payload.interaction.kind })
      await refreshSession()
    } catch (error) {
      errorMessage.value = toUserMessage(error)
    }
  }

  watch(
    () => analysisOperation.value?.status,
    async (status, previousStatus) => {
      if (!status || status === previousStatus || !recordingId.value) {
        return
      }
      if (status === 'succeeded') {
        try {
          const response = await getRecordingAnalysis(recordingId.value)
          analysis.value = response.analysis
          successMessage.value = t('recording.analysisCompleted')
          errorMessage.value = null
        } catch (error) {
          errorMessage.value = toUserMessage(error)
        }
        return
      }
      if (status === 'failed') {
        errorMessage.value = analysisOperation.value?.error_message
          ?? analysisProgressError.value
          ?? t('recording.analysisFailed')
      }
    },
  )

  return {
    session,
    events,
    timeline,
    sessionQuery,
    timelineQuery,
    analysis,
    exportedCase,
    replayResult,
    bridge,
    loading,
    errorMessage,
    successMessage,
    analysisModalOpen,
    analysisEvents,
    analysisProgressError,
    analysisOperation,
    analysisOperationRunning,
    createSession,
    beginSession,
    stopSession,
    analyzeSession,
    exportCase,
    replayCase,
    closeAnalysisModal,
    handleAnalysisExport,
    handleInteractionForwarded,
    refreshSession,
  }
}
