import type { components } from '../contracts/generated/local-api'
import { client, unwrapData } from './client'

export type AppListData = components['schemas']['AppListData']
export type AppListItem = components['schemas']['AppListItemData']
export type AppDetailData = components['schemas']['AppDetailData']
export type AppUpsertRequest = components['schemas']['AppUpsertRequest']
export type DeleteAppData = components['schemas']['DeleteAppData']

export async function listApps(input?: { platform?: string }): Promise<AppListItem[]> {
  const data = await unwrapData<components['schemas']['SuccessResponse_AppListData_']>(
    client.GET('/v1/apps', {
      params: {
        query: {
          platform: input?.platform ?? null,
        },
      },
    })
  )
  return data.items ?? []
}

export async function getAppDetail(appId: string): Promise<AppDetailData> {
  return unwrapData<components['schemas']['SuccessResponse_AppDetailData_']>(
    client.GET('/v1/apps/{app_id}', {
      params: {
        path: {
          app_id: appId,
        },
      },
    })
  )
}

export async function createApp(request: AppUpsertRequest): Promise<AppDetailData> {
  return unwrapData<components['schemas']['SuccessResponse_AppDetailData_']>(
    client.POST('/v1/apps', {
      body: request,
    })
  )
}

export async function updateApp(appId: string, request: AppUpsertRequest): Promise<AppDetailData> {
  return unwrapData<components['schemas']['SuccessResponse_AppDetailData_']>(
    client.PUT('/v1/apps/{app_id}', {
      params: {
        path: {
          app_id: appId,
        },
      },
      body: request,
    })
  )
}

export async function deleteApp(appId: string): Promise<DeleteAppData> {
  return unwrapData<components['schemas']['SuccessResponse_DeleteAppData_']>(
    client.DELETE('/v1/apps/{app_id}', {
      params: {
        path: {
          app_id: appId,
        },
      },
    })
  )
}
