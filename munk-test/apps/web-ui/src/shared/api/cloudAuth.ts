import type { components } from '../contracts/generated/local-api'
import { client, unwrapData } from './client'

export type CloudSessionSummaryData = components['schemas']['CloudSessionSummaryData']
export type CloudLoginStartData = components['schemas']['CloudLoginStartData']
export type CloudWorkspacesData = components['schemas']['CloudWorkspacesData']

export async function getCloudAuthSession(): Promise<CloudSessionSummaryData> {
  return unwrapData<components['schemas']['SuccessResponse_CloudSessionSummaryData_']>(
    client.GET('/v1/cloud/auth/session'),
  )
}

export async function startCloudAuthLogin(): Promise<CloudLoginStartData> {
  return unwrapData<components['schemas']['SuccessResponse_CloudLoginStartData_']>(
    client.POST('/v1/cloud/auth/login', {}),
  )
}

export async function logoutCloudAuth(): Promise<CloudSessionSummaryData> {
  return unwrapData<components['schemas']['SuccessResponse_CloudSessionSummaryData_']>(
    client.POST('/v1/cloud/auth/logout', {}),
  )
}

export async function listCloudAuthWorkspaces(): Promise<CloudWorkspacesData> {
  return unwrapData<components['schemas']['SuccessResponse_CloudWorkspacesData_']>(
    client.GET('/v1/cloud/auth/workspaces'),
  )
}
