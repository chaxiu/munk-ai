import { useMutation, useQueryClient } from '@tanstack/vue-query'

import { disableSchedule, enableSchedule, updateSchedule, type ScheduleUpsertRequest } from '@/shared/api/schedules'
import { schedulesKeys } from './schedulesKeys'

export function useScheduleMutations() {
  const queryClient = useQueryClient()

  async function invalidateSchedule(scheduleId: string) {
    await queryClient.invalidateQueries({ queryKey: schedulesKeys.list() })
    await queryClient.invalidateQueries({ queryKey: schedulesKeys.detail(scheduleId) })
    await queryClient.invalidateQueries({ queryKey: schedulesKeys.all })
  }

  return {
    enableSchedule: useMutation({
      mutationKey: [...schedulesKeys.all, 'enable'] as const,
      mutationFn: (scheduleId: string) => enableSchedule(scheduleId),
      onSuccess: async (_, scheduleId) => {
        await invalidateSchedule(scheduleId)
      },
    }),
    disableSchedule: useMutation({
      mutationKey: [...schedulesKeys.all, 'disable'] as const,
      mutationFn: (scheduleId: string) => disableSchedule(scheduleId),
      onSuccess: async (_, scheduleId) => {
        await invalidateSchedule(scheduleId)
      },
    }),
    updateSchedule: useMutation({
      mutationKey: [...schedulesKeys.all, 'update'] as const,
      mutationFn: (input: { scheduleId: string, request: ScheduleUpsertRequest }) => updateSchedule(input.scheduleId, input.request),
      onSuccess: async (_, input) => {
        await invalidateSchedule(input.scheduleId)
      },
    }),
  }
}
