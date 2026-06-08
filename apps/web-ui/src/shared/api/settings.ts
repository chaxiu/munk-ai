import type { components } from '../contracts/generated/local-api'
import { client, unwrapData } from './client'

export type SettingsConfigData = components['schemas']['SettingsConfigData']
export type SettingsConfigUpsertRequest = components['schemas']['SettingsConfigUpsertRequest']

export async function getSettingsConfig(): Promise<SettingsConfigData> {
  return unwrapData<components['schemas']['SuccessResponse_SettingsConfigData_']>(
    client.GET('/v1/settings/config')
  )
}

export async function updateSettingsConfig(
  request: SettingsConfigUpsertRequest,
): Promise<SettingsConfigData> {
  return unwrapData<components['schemas']['SuccessResponse_SettingsConfigData_']>(
    client.PUT('/v1/settings/config', {
      body: request,
    })
  )
}
