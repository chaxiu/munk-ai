import type { components } from '../contracts/generated/local-api'
import { client, unwrapData } from './client'

export type DashboardSummaryData = components['schemas']['DashboardSummaryData']

export async function getDashboardSummary(): Promise<DashboardSummaryData> {
  return unwrapData<components['schemas']['SuccessResponse_DashboardSummaryData_']>(
    client.GET('/v1/dashboard/summary')
  )
}
