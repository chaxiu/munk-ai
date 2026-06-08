import type { components } from '../contracts/generated/local-api'
import { client, unwrapData } from './client'

export type PlanListData = components['schemas']['PlanListData']
export type PlanListItemData = components['schemas']['PlanListItemData']
export type PlanDetailData = components['schemas']['PlanDetailData']
export type PlanImportData = components['schemas']['PlanImportData']
export type PlanImportRequest = components['schemas']['PlanImportRequest']
export type CaseBriefData = components['schemas']['CaseBriefData']
export type CaseDeleteData = components['schemas']['CaseDeleteData']
export type CaseDetailData = components['schemas']['CaseDetailData']
export type CaseUpsertRequest = components['schemas']['CaseUpsertRequest']
export type CaseUpdateRequest = components['schemas']['CaseUpdateRequest']
export type CaseSearchData = components['schemas']['CaseSearchData']
export type CaseSearchItemData = components['schemas']['CaseSearchItemData']
export type TestCasePayload = components['schemas']['TestCasePayload']
export type CaseRewritePreviewRequest = components['schemas']['CaseRewritePreviewRequest']
export type CaseRewritePreviewData = components['schemas']['CaseRewritePreviewData']

export async function listPlans(input?: {
  appId?: string
  source?: string
  caseCountMode?: 'all' | 'single' | 'multi'
  includeLatestRun?: boolean
  limit?: number
  offset?: number
}): Promise<PlanListData> {
  return unwrapData<components['schemas']['SuccessResponse_PlanListData_']>(
    client.GET('/v1/plans', {
      params: {
        query: {
          app_id: input?.appId ?? undefined,
          source: input?.source ?? undefined,
          case_count_mode: input?.caseCountMode === 'all' ? undefined : input?.caseCountMode ?? undefined,
          include_latest_run: input?.includeLatestRun ?? undefined,
          limit: input?.limit ?? 20,
          offset: input?.offset ?? 0,
        },
      },
    })
  )
}

export async function getPlanDetail(appId: string, planId: string): Promise<PlanDetailData> {
  return unwrapData<components['schemas']['SuccessResponse_PlanDetailData_']>(
    client.GET('/v1/plans/{app_id}/{plan_id}', {
      params: {
        path: {
          app_id: appId,
          plan_id: planId,
        },
      },
    })
  )
}

export async function importPlan(request: PlanImportRequest): Promise<PlanImportData> {
  return unwrapData<components['schemas']['SuccessResponse_PlanImportData_']>(
    client.POST('/v1/plans:import', {
      body: request,
    })
  )
}

export async function getCaseDetail(appId: string, planId: string, caseId: string): Promise<CaseDetailData> {
  return unwrapData<components['schemas']['SuccessResponse_CaseDetailData_']>(
    client.GET('/v1/plans/{app_id}/{plan_id}/cases/{case_id}', {
      params: {
        path: {
          app_id: appId,
          plan_id: planId,
          case_id: caseId,
        },
      },
    })
  )
}

export async function updateCaseDetail(
  appId: string,
  planId: string,
  caseId: string,
  request: CaseUpdateRequest,
): Promise<CaseDetailData> {
  return unwrapData<components['schemas']['SuccessResponse_CaseDetailData_']>(
    client.PUT('/v1/plans/{app_id}/{plan_id}/cases/{case_id}', {
      params: {
        path: {
          app_id: appId,
          plan_id: planId,
          case_id: caseId,
        },
      },
      body: request,
    })
  )
}

export async function addCase(
  appId: string,
  planId: string,
  request: CaseUpsertRequest,
): Promise<CaseDetailData> {
  return unwrapData<components['schemas']['SuccessResponse_CaseDetailData_']>(
    client.POST('/v1/plans/{app_id}/{plan_id}/cases', {
      params: {
        path: {
          app_id: appId,
          plan_id: planId,
        },
      },
      body: request,
    })
  )
}

export async function replaceCase(
  appId: string,
  planId: string,
  caseId: string,
  request: CaseUpsertRequest,
): Promise<CaseDetailData> {
  return unwrapData<components['schemas']['SuccessResponse_CaseDetailData_']>(
    client.PUT('/v1/plans/{app_id}/{plan_id}/cases/{case_id}/replace', {
      params: {
        path: {
          app_id: appId,
          plan_id: planId,
          case_id: caseId,
        },
      },
      body: request,
    })
  )
}

export async function rewriteCasePreview(
  appId: string,
  planId: string,
  caseId: string,
  request: CaseRewritePreviewRequest,
): Promise<CaseRewritePreviewData> {
  return unwrapData<components['schemas']['SuccessResponse_CaseRewritePreviewData_']>(
    client.POST('/v1/plans/{app_id}/{plan_id}/cases/{case_id}/rewrite-preview', {
      params: {
        path: {
          app_id: appId,
          plan_id: planId,
          case_id: caseId,
        },
      },
      body: request,
    })
  )
}

export async function deleteCase(
  appId: string,
  planId: string,
  caseId: string,
): Promise<CaseDeleteData> {
  return unwrapData<components['schemas']['SuccessResponse_CaseDeleteData_']>(
    client.DELETE('/v1/plans/{app_id}/{plan_id}/cases/{case_id}', {
      params: {
        path: {
          app_id: appId,
          plan_id: planId,
          case_id: caseId,
        },
      },
    })
  )
}

export async function searchCases(input?: {
  appId?: string
  planId?: string
  caseId?: string
  query?: string
  isCoreCase?: boolean
  startMode?: string
  limit?: number
  offset?: number
}): Promise<CaseSearchData> {
  return unwrapData<components['schemas']['SuccessResponse_CaseSearchData_']>(
    client.GET('/v1/plans/cases', {
      params: {
        query: {
          app_id: input?.appId ?? undefined,
          plan_id: input?.planId ?? undefined,
          case_id: input?.caseId ?? undefined,
          query: input?.query ?? undefined,
          is_core_case: input?.isCoreCase ?? undefined,
          start_mode: input?.startMode ?? undefined,
          limit: input?.limit ?? 20,
          offset: input?.offset ?? 0,
        },
      },
    })
  )
}
