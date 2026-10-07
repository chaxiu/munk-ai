import type { components } from '../contracts/generated/local-api'
import { client, unwrapData } from './client'

export type CloudLinkData = components['schemas']['CloudLinkData']
export type CloudLinkItemData = components['schemas']['CloudLinkItemData']
export type CloudLinksData = components['schemas']['CloudLinksData']
export type CloudLinkUpsertRequest = components['schemas']['CloudLinkUpsertRequest']
export type CloudLinkActiveRequest = components['schemas']['CloudLinkActiveRequest']
export type CloudAppsData = components['schemas']['CloudAppsData']
export type CloudAppSummaryData = components['schemas']['CloudAppSummaryData']
export type CloudSyncStatusData = components['schemas']['CloudSyncStatusData']
export type CloudSyncPullResultData = components['schemas']['CloudSyncPullResultData']
export type CloudSyncPushResultData = components['schemas']['CloudSyncPushResultData']
export type CloudSyncPublishRequest = components['schemas']['CloudSyncPublishRequest']
export type CloudSyncPublishResultData = components['schemas']['CloudSyncPublishResultData']

export async function getCloudLinks(): Promise<CloudLinksData> {
  return unwrapData<components['schemas']['SuccessResponse_CloudLinksData_']>(
    client.GET('/v1/cloud/links'),
  )
}

export async function putCloudLink(
  body: CloudLinkUpsertRequest,
): Promise<CloudLinkData> {
  return unwrapData<components['schemas']['SuccessResponse_CloudLinkData_']>(
    client.PUT('/v1/cloud/links', {
      body,
    }),
  )
}

export async function putCloudLinkActive(
  body: CloudLinkActiveRequest,
): Promise<CloudLinksData> {
  return unwrapData<components['schemas']['SuccessResponse_CloudLinksData_']>(
    client.PUT('/v1/cloud/links/active', {
      body,
    }),
  )
}

export async function deleteCloudLink(appId: string): Promise<CloudLinksData> {
  return unwrapData<components['schemas']['SuccessResponse_CloudLinksData_']>(
    client.DELETE('/v1/cloud/links/{app_id}', {
      params: {
        path: {
          app_id: appId,
        },
      },
    }),
  )
}

export async function listCloudApps(workspaceId: string): Promise<CloudAppsData> {
  return unwrapData<components['schemas']['SuccessResponse_CloudAppsData_']>(
    client.GET('/v1/cloud/apps', {
      params: {
        query: {
          workspace_id: workspaceId,
        },
      },
    }),
  )
}

export async function getCloudSyncStatus(appId?: string | null): Promise<CloudSyncStatusData> {
  return unwrapData<components['schemas']['SuccessResponse_CloudSyncStatusData_']>(
    client.GET('/v1/cloud/sync/status', {
      params: {
        query: appId ? { app_id: appId } : {},
      },
    }),
  )
}

export async function pullCloudSync(
  force = false,
  appId?: string | null,
): Promise<CloudSyncPullResultData> {
  return unwrapData<components['schemas']['SuccessResponse_CloudSyncPullResultData_']>(
    client.POST('/v1/cloud/sync/pull', {
      body: { force, app_id: appId ?? null },
    }),
  )
}

export async function pushCloudSync(
  force = false,
  appId?: string | null,
): Promise<CloudSyncPushResultData> {
  return unwrapData<components['schemas']['SuccessResponse_CloudSyncPushResultData_']>(
    client.POST('/v1/cloud/sync/push', {
      body: { force, app_id: appId ?? null },
    }),
  )
}

export async function publishCloudSync(
  body: CloudSyncPublishRequest,
): Promise<CloudSyncPublishResultData> {
  return unwrapData<components['schemas']['SuccessResponse_CloudSyncPublishResultData_']>(
    client.POST('/v1/cloud/sync/publish', {
      body,
    }),
  )
}
