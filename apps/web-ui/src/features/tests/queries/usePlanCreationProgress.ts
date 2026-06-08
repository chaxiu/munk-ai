import { computed, onUnmounted, ref, toValue, watch, type MaybeRefOrGetter } from 'vue'

import {
  getOperation,
  listOperationEvents,
  type OperationDetailData,
  type OperationEventsData,
} from '@/shared/api/operations'

type OperationEventRecord = NonNullable<OperationEventsData['items']>[number]

const POLL_INTERVAL_MS = 2000

export function usePlanCreationProgress(operationId: MaybeRefOrGetter<string>) {
  const operation = ref<OperationDetailData | null>(null)
  const events = ref<OperationEventRecord[]>([])
  const afterSeq = ref(0)
  const loading = ref(false)
  const error = ref<unknown>(null)
  const polling = ref(false)
  let timer: number | null = null
  let pollSessionId = 0

  const isFinished = computed(() => {
    const status = operation.value?.status
    return status === 'succeeded' || status === 'failed' || status === 'cancelled'
  })

  function stopPolling() {
    if (timer !== null) {
      window.clearInterval(timer)
      timer = null
    }
  }

  async function pollOnce() {
    const currentPollSessionId = pollSessionId
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
      if (currentPollSessionId !== pollSessionId || currentOperationId !== toValue(operationId)) {
        return
      }
      operation.value = nextOperation
      const nextItems = nextEvents.items ?? []
      if (nextItems.length > 0) {
        events.value = [...events.value, ...nextItems]
      }
      afterSeq.value = nextEvents.next_after_seq
      error.value = null
    } catch (nextError) {
      error.value = nextError
    } finally {
      loading.value = false
      polling.value = false
      if (isFinished.value) {
        stopPolling()
      }
    }
  }

  watch(
    () => toValue(operationId),
    (nextOperationId) => {
      pollSessionId += 1
      stopPolling()
      operation.value = null
      events.value = []
      afterSeq.value = 0
      error.value = null
      polling.value = false
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
    pollSessionId += 1
    stopPolling()
  })

  return {
    operation,
    events,
    loading,
    error,
    polling,
    isFinished,
    refetch: pollOnce,
  }
}
