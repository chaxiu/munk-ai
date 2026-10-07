import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { computed, defineComponent, h, ref } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type {
  OperationDetailData,
  OperationEventsData,
} from '@/shared/api/operations'
import { useRunEventsQuery } from '../useRunEventsQuery'

const { getOperationMock, listOperationEventsMock } = vi.hoisted(() => ({
  getOperationMock: vi.fn<typeof import('@/shared/api/operations').getOperation>(),
  listOperationEventsMock: vi.fn<typeof import('@/shared/api/operations').listOperationEvents>(),
}))

vi.mock('@/shared/api/operations', async () => {
  const actual = await vi.importActual<typeof import('@/shared/api/operations')>('@/shared/api/operations')
  return {
    ...actual,
    getOperation: getOperationMock,
    listOperationEvents: listOperationEventsMock,
  }
})

type RunEventsQueryState = ReturnType<typeof useRunEventsQuery>

const operationIdState = ref('op-1')
let queryState: RunEventsQueryState

const TestHarness = defineComponent({
  setup() {
    queryState = useRunEventsQuery(computed(() => operationIdState.value))
    return () => h('div')
  },
})

function buildOperation(status: OperationDetailData['status']): OperationDetailData {
  return {
    operation_id: 'op-1',
    kind: 'case_run',
    status,
    cancel_requested: false,
    is_batch: false,
    created_at: '2026-01-01T00:00:00Z',
    finished_at: null,
    started_at: '2026-01-01T00:00:00Z',
    device_ref: null,
    parent_operation_id: null,
    title: 'Test run',
    run_type: 'case_run',
  }
}

function buildEvents(
  afterSeq: number,
  nextAfterSeq: number,
  itemSeqs: number[],
): OperationEventsData {
  return {
    operation_id: 'op-1',
    after_seq: afterSeq,
    limit: 200,
    next_after_seq: nextAfterSeq,
    items: itemSeqs.map((seq) => ({
      seq,
      operation_id: 'op-1',
      timestamp: `2026-01-01T00:00:0${seq}Z`,
      event_type: `event_${seq}`,
      message: `event ${seq}`,
      agent_role: null,
      timeline_scope: null,
      timeline_phase: null,
      attempt_index: null,
      parent_operation_id: null,
      child_operation_id: null,
      app_id: null,
      plan_id: null,
      case_id: null,
      summary: null,
      data_json: {},
    })),
  }
}

enableAutoUnmount(afterEach)

describe('useRunEventsQuery', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    operationIdState.value = 'op-1'
    getOperationMock.mockReset()
    listOperationEventsMock.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('appends incremental events and stops after terminal drain reaches no new items', async () => {
    getOperationMock
      .mockResolvedValueOnce(buildOperation('running'))
      .mockResolvedValueOnce(buildOperation('running'))
      .mockResolvedValueOnce(buildOperation('succeeded'))
      .mockResolvedValueOnce(buildOperation('succeeded'))

    listOperationEventsMock
      .mockResolvedValueOnce(buildEvents(0, 1, [1]))
      .mockResolvedValueOnce(buildEvents(1, 2, [2]))
      .mockResolvedValueOnce(buildEvents(2, 3, [3]))
      .mockResolvedValueOnce(buildEvents(3, 3, []))

    mount(TestHarness)
    await flushPromises()

    expect(queryState.data.value?.items?.map((item) => item.seq)).toEqual([1])
    expect(listOperationEventsMock).toHaveBeenNthCalledWith(1, 'op-1', { afterSeq: 0, limit: 200 })

    await vi.advanceTimersByTimeAsync(2000)
    await flushPromises()

    expect(queryState.data.value?.items?.map((item) => item.seq)).toEqual([1, 2])
    expect(listOperationEventsMock).toHaveBeenNthCalledWith(2, 'op-1', { afterSeq: 1, limit: 200 })

    await vi.advanceTimersByTimeAsync(2000)
    await flushPromises()

    expect(queryState.data.value?.items?.map((item) => item.seq)).toEqual([1, 2, 3])
    expect(listOperationEventsMock).toHaveBeenNthCalledWith(3, 'op-1', { afterSeq: 2, limit: 200 })

    await vi.advanceTimersByTimeAsync(2000)
    await flushPromises()

    expect(queryState.data.value?.items?.map((item) => item.seq)).toEqual([1, 2, 3])
    expect(listOperationEventsMock).toHaveBeenNthCalledWith(4, 'op-1', { afterSeq: 3, limit: 200 })

    await vi.advanceTimersByTimeAsync(4000)
    await flushPromises()

    expect(listOperationEventsMock).toHaveBeenCalledTimes(4)
    expect(getOperationMock).toHaveBeenCalledTimes(4)
  })

  it('keeps manual refetch working after polling has naturally stopped', async () => {
    getOperationMock
      .mockResolvedValueOnce(buildOperation('succeeded'))
      .mockResolvedValueOnce(buildOperation('succeeded'))
      .mockResolvedValueOnce(buildOperation('succeeded'))

    listOperationEventsMock
      .mockResolvedValueOnce(buildEvents(0, 1, [1]))
      .mockResolvedValueOnce(buildEvents(1, 1, []))
      .mockResolvedValueOnce(buildEvents(1, 2, [2]))

    mount(TestHarness)
    await flushPromises()

    await vi.advanceTimersByTimeAsync(2000)
    await flushPromises()

    expect(listOperationEventsMock).toHaveBeenCalledTimes(2)
    expect(queryState.data.value?.items?.map((item) => item.seq)).toEqual([1])

    await queryState.refetch()
    await flushPromises()

    expect(listOperationEventsMock).toHaveBeenCalledTimes(3)
    expect(listOperationEventsMock).toHaveBeenLastCalledWith('op-1', { afterSeq: 1, limit: 200 })
    expect(queryState.data.value?.items?.map((item) => item.seq)).toEqual([1, 2])
  })
})
