import type { components } from '../contracts/generated/local-api'
import { client, unwrapData } from './client'

export type ScheduleUpsertRequest = components['schemas']['ScheduleUpsertRequest']
export type ScheduleDetailData = components['schemas']['ScheduleDetailData']
export type ScheduleListData = components['schemas']['ScheduleListData']
export type ScheduleRunListData = components['schemas']['ScheduleRunListData']
export type ScheduleRunSummaryData = components['schemas']['ScheduleRunSummaryData']
export type ScheduleSummaryData = components['schemas']['ScheduleSummaryData']
export type ScheduleRuntimeOverrides = NonNullable<ScheduleUpsertRequest['runtime_overrides']>

export type ListSchedulesInput = {
  enabled?: boolean
  appId?: string
  keyword?: string
  limit?: number
  offset?: number
}

export async function createSchedule(request: ScheduleUpsertRequest): Promise<ScheduleDetailData> {
  return unwrapData<components['schemas']['SuccessResponse_ScheduleDetailData_']>(
    client.POST('/v1/schedules', {
      body: request,
    })
  )
}

export async function listSchedules(input?: ListSchedulesInput): Promise<ScheduleListData> {
  return unwrapData<components['schemas']['SuccessResponse_ScheduleListData_']>(
    client.GET('/v1/schedules', {
      params: {
        query: {
          enabled: input?.enabled,
          app_id: input?.appId,
          keyword: input?.keyword,
          limit: input?.limit,
          offset: input?.offset,
        },
      },
    })
  )
}

export async function getSchedule(scheduleId: string): Promise<ScheduleDetailData> {
  return unwrapData<components['schemas']['SuccessResponse_ScheduleDetailData_']>(
    client.GET('/v1/schedules/{schedule_id}', {
      params: {
        path: {
          schedule_id: scheduleId,
        },
      },
    })
  )
}

export async function updateSchedule(
  scheduleId: string,
  request: ScheduleUpsertRequest
): Promise<ScheduleDetailData> {
  return unwrapData<components['schemas']['SuccessResponse_ScheduleDetailData_']>(
    client.PUT('/v1/schedules/{schedule_id}', {
      params: {
        path: {
          schedule_id: scheduleId,
        },
      },
      body: request,
    })
  )
}

export async function listScheduleRuns(
  scheduleId: string,
  input?: { limit?: number }
): Promise<ScheduleRunListData> {
  return unwrapData<components['schemas']['SuccessResponse_ScheduleRunListData_']>(
    client.GET('/v1/schedules/{schedule_id}/runs', {
      params: {
        path: {
          schedule_id: scheduleId,
        },
        query: {
          limit: input?.limit ?? 20,
        },
      },
    })
  )
}

export async function enableSchedule(scheduleId: string): Promise<ScheduleSummaryData> {
  return unwrapData<components['schemas']['SuccessResponse_ScheduleSummaryData_']>(
    client.POST('/v1/schedules/{schedule_id}:enable', {
      params: {
        path: {
          schedule_id: scheduleId,
        },
      },
    })
  )
}

export async function disableSchedule(scheduleId: string): Promise<ScheduleSummaryData> {
  return unwrapData<components['schemas']['SuccessResponse_ScheduleSummaryData_']>(
    client.POST('/v1/schedules/{schedule_id}:disable', {
      params: {
        path: {
          schedule_id: scheduleId,
        },
      },
    })
  )
}
