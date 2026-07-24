import { computed, onUnmounted, ref, toValue, watch, type MaybeRefOrGetter } from 'vue'

import {
  getOperation,
  listOperationEvents,
  type OperationEventsData,
} from '@/shared/api/operations'
import { DEFAULT_POLL_INTERVAL_MS } from '@/shared/query/defaults'

const EVENTS_PAGE_SIZE = 200

function isTerminalStatus(status: string | null | undefined): boolean {
  return status === 'succeeded' || status === 'failed' || status === 'cancelled' || status === 'interrupted'
}

export function useRunEventsQuery(operationId: MaybeRefOrGetter<string>) {
  const data = ref<OperationEventsData | null>(null)
  const isFetching = ref(false)
  const error = ref<unknown>(null)
  const afterSeq = ref(0)
  const drainingAfterTerminal = ref(false)
  let timer: number | null = null
  let pollSessionId = 0

  function stopPolling() {
    if (timer !== null) {
      window.clearInterval(timer)
      timer = null
    }
  }

  async function pollOnce() {
    const currentPollSessionId = pollSessionId
    const currentOperationId = toValue(operationId)
    if (!currentOperationId || isFetching.value) {
      return { data: data.value }
    }

    isFetching.value = true

    try {
      const [nextOperation, nextEvents] = await Promise.all([
        getOperation(currentOperationId),
        listOperationEvents(currentOperationId, {
          afterSeq: afterSeq.value,
          limit: EVENTS_PAGE_SIZE,
        }),
      ])

      if (currentPollSessionId !== pollSessionId || currentOperationId !== toValue(operationId)) {
        return { data: data.value }
      }

      const previousItems = data.value?.items ?? []
      const nextItems = nextEvents.items ?? []
      data.value = {
        ...nextEvents,
        items: previousItems.length > 0 ? [...previousItems, ...nextItems] : nextItems,
      }
      afterSeq.value = nextEvents.next_after_seq
      error.value = null

      if (isTerminalStatus(nextOperation.status)) {
        if (drainingAfterTerminal.value && nextItems.length === 0) {
          stopPolling()
        } else {
          drainingAfterTerminal.value = true
        }
      } else {
        drainingAfterTerminal.value = false
      }

      return { data: data.value }
    } catch (nextError) {
      error.value = nextError
      return { data: data.value }
    } finally {
      isFetching.value = false
    }
  }

  watch(
    () => toValue(operationId),
    (nextOperationId) => {
      pollSessionId += 1
      stopPolling()
      data.value = null
      isFetching.value = false
      error.value = null
      afterSeq.value = 0
      drainingAfterTerminal.value = false

      if (!nextOperationId) {
        return
      }

      void pollOnce()
      timer = window.setInterval(() => {
        void pollOnce()
      }, DEFAULT_POLL_INTERVAL_MS)
    },
    { immediate: true },
  )

  onUnmounted(() => {
    pollSessionId += 1
    stopPolling()
  })

  return {
    data: computed(() => data.value),
    isFetching: computed(() => isFetching.value),
    error: computed(() => error.value),
    refetch: pollOnce,
  }
}
