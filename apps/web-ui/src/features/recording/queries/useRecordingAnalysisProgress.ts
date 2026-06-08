import { onUnmounted, ref, toValue, watch, type MaybeRefOrGetter } from 'vue'

import {
  getOperation,
  listOperationEvents,
  type OperationDetailData,
  type OperationEventsData,
} from '@/shared/api/operations'

type OperationEventRecord = NonNullable<OperationEventsData['items']>[number]

const POLL_INTERVAL_MS = 2000

export function useRecordingAnalysisProgress(operationId: MaybeRefOrGetter<string | null | undefined>) {
  const operation = ref<OperationDetailData | null>(null)
  const events = ref<OperationEventRecord[]>([])
  const afterSeq = ref(0)
  const loading = ref(false)
  const error = ref<unknown>(null)
  const polling = ref(false)
  let timer: number | null = null

  function stopPolling() {
    if (timer !== null) {
      window.clearInterval(timer)
      timer = null
    }
  }

  function isTerminalStatus(status: string | null | undefined): boolean {
    return status === 'succeeded' || status === 'failed' || status === 'cancelled'
  }

  async function pollOnce() {
    const currentOperationId = toValue(operationId)
    if (!currentOperationId || polling.value) {
      return
    }
    polling.value = true
    try {
      const [nextOperation, nextEvents] = await Promise.all([
        getOperation(currentOperationId),
        listOperationEvents(currentOperationId, {
          afterSeq: afterSeq.value,
          limit: 100,
        }),
      ])
      operation.value = nextOperation
      const nextItems = nextEvents.items ?? []
      if (nextItems.length > 0) {
        events.value = [...events.value, ...nextItems]
      }
      afterSeq.value = nextEvents.next_after_seq
      error.value = null
      if (isTerminalStatus(nextOperation.status)) {
        stopPolling()
      }
    } catch (nextError) {
      error.value = nextError
    } finally {
      loading.value = false
      polling.value = false
    }
  }

  watch(
    () => toValue(operationId),
    (nextOperationId) => {
      stopPolling()
      operation.value = null
      events.value = []
      afterSeq.value = 0
      error.value = null
      loading.value = Boolean(nextOperationId)
      if (!nextOperationId) {
        return
      }
      void pollOnce()
      timer = window.setInterval(() => {
        void pollOnce()
      }, POLL_INTERVAL_MS)
    },
    { immediate: true },
  )

  onUnmounted(() => {
    stopPolling()
  })

  return {
    operation,
    events,
    loading,
    error,
    polling,
    isFinished: () => isTerminalStatus(operation.value?.status),
    refetch: pollOnce,
  }
}
