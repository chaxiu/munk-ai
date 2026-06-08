import type { components, operations } from '../contracts/generated/local-api'
import { client, unwrapData } from './client'

export type OperationChildItemData = components['schemas']['OperationChildItemData']
export type BatchRunAggregateData = components['schemas']['BatchRunAggregateData']
export type OperationChildrenData = components['schemas']['OperationChildrenData']
export type OperationDetailData = components['schemas']['OperationDetailData']
export type OperationListData = components['schemas']['OperationListData']
export type OperationSummaryData = components['schemas']['OperationSummaryData']
export type OperationArtifactsData = components['schemas']['OperationArtifactsData']
export type RunArtifactChildrenData = components['schemas']['RunArtifactChildrenData']
export type RunArtifactChildItemData = components['schemas']['RunArtifactChildItemData']
export type RunArtifactContentData = components['schemas']['RunArtifactContentData']
export type RunArtifactGroupData = components['schemas']['RunArtifactGroupData']
export type RunArtifactItemData = components['schemas']['RunArtifactItemData']
export type CancelOperationData = components['schemas']['CancelOperationData']
export type OperationEventsData = components['schemas']['OperationEventsData']
export type ReproduceOperationData = components['schemas']['ReproduceOperationData']
type RunsListQuery = NonNullable<operations['runs_list_v1_runs_get']['parameters']['query']>

export type OperationStatus = RunsListQuery['status']
export type OperationKind = RunsListQuery['kind'] | 'run_plans'
export type RunsSurface = RunsListQuery['surface']

export async function listOperations(input?: {
  limit?: number
  offset?: number
  status?: OperationStatus
  kind?: OperationKind
  deviceRef?: string
  surface?: RunsSurface
  verificationVerdict?: string
  platform?: string
  query?: string
  runType?: string
}): Promise<OperationSummaryData[]> {
  const data = await listRunsPage(input)
  return data.items ?? []
}

export async function listRunsPage(input?: {
  limit?: number
  offset?: number
  status?: OperationStatus
  kind?: OperationKind
  deviceRef?: string
  surface?: RunsSurface
  verificationVerdict?: string
  platform?: string
  query?: string
  runType?: string
}): Promise<OperationListData> {
  const query: RunsListQuery = {
    limit: input?.limit ?? 20,
    offset: input?.offset ?? 0,
    status: input?.status ?? undefined,
    kind: (input?.kind ?? undefined) as RunsListQuery['kind'],
    device_ref: input?.deviceRef ?? undefined,
    surface: input?.surface ?? undefined,
    verification_verdict: input?.verificationVerdict ?? undefined,
    platform: input?.platform ?? undefined,
    query: input?.query ?? undefined,
    run_type: input?.runType ?? undefined,
  }
  return unwrapData<components['schemas']['SuccessResponse_OperationListData_']>(
    client.GET('/v1/runs', {
      params: {
        query
      }
    })
  )
}

export async function getOperation(operationId: string): Promise<OperationDetailData> {
  return unwrapData<components['schemas']['SuccessResponse_OperationDetailData_']>(
    client.GET('/v1/runs/{operation_id}', {
      params: {
        path: {
          operation_id: operationId
        }
      }
    })
  )
}

export async function getOperationChildren(operationId: string): Promise<OperationChildrenData> {
  return unwrapData<components['schemas']['SuccessResponse_OperationChildrenData_']>(
    client.GET('/v1/runs/{operation_id}/children', {
      params: {
        path: {
          operation_id: operationId
        }
      }
    })
  )
}

export async function listOperationEvents(
  operationId: string,
  input?: { afterSeq?: number, limit?: number }
): Promise<OperationEventsData> {
  return unwrapData<components['schemas']['SuccessResponse_OperationEventsData_']>(
    client.GET('/v1/runs/{operation_id}/events', {
      params: {
        path: {
          operation_id: operationId
        },
        query: {
          after_seq: input?.afterSeq ?? 0,
          limit: input?.limit ?? 100
        }
      }
    })
  )
}

export async function getOperationArtifacts(operationId: string): Promise<OperationArtifactsData> {
  return unwrapData<components['schemas']['SuccessResponse_OperationArtifactsData_']>(
    client.GET('/v1/runs/{operation_id}/artifacts', {
      params: {
        path: {
          operation_id: operationId
        }
      }
    })
  )
}

export async function getOperationArtifactContent(
  operationId: string,
  artifactId: string,
  input?: { maxBytes?: number }
): Promise<RunArtifactContentData> {
  return unwrapData<components['schemas']['SuccessResponse_RunArtifactContentData_']>(
    client.GET('/v1/runs/{operation_id}/artifacts/{artifact_id}/content', {
      params: {
        path: {
          operation_id: operationId,
          artifact_id: artifactId
        },
        query: {
          max_bytes: input?.maxBytes ?? undefined
        }
      }
    })
  )
}

export async function listOperationArtifactChildren(
  operationId: string,
  artifactId: string
): Promise<RunArtifactChildrenData> {
  return unwrapData<components['schemas']['SuccessResponse_RunArtifactChildrenData_']>(
    client.GET('/v1/runs/{operation_id}/artifacts/{artifact_id}/children', {
      params: {
        path: {
          operation_id: operationId,
          artifact_id: artifactId,
        },
      },
    })
  )
}

export function getOperationArtifactDownloadUrl(operationId: string, artifactId: string): string {
  return `/v1/runs/${encodeURIComponent(operationId)}/artifacts/${encodeURIComponent(artifactId)}/download`
}

export async function cancelOperation(operationId: string): Promise<CancelOperationData> {
  return unwrapData<components['schemas']['SuccessResponse_CancelOperationData_']>(
    client.POST('/v1/runs/{operation_id}/cancel', {
      params: {
        path: {
          operation_id: operationId
        }
      }
    })
  )
}

export async function reproduceOperation(operationId: string): Promise<ReproduceOperationData> {
  return unwrapData<components['schemas']['SuccessResponse_ReproduceOperationData_']>(
    client.POST('/v1/runs/{operation_id}/reproduce', {
      params: {
        path: {
          operation_id: operationId
        }
      }
    })
  )
}
