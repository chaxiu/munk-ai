import type { components } from '../contracts/generated/local-api'
import { client, unwrapData } from './client'

export type KnowledgeSource = components['schemas']['KnowledgeSource']
export type KnowledgeCard = components['schemas']['ScreenKnowledgeCard']
  | components['schemas']['FlowKnowledgeCard']
  | components['schemas']['AssertionKnowledgeCard']
  | components['schemas']['IssueKnowledgeCard']
  | components['schemas']['DataKnowledgeCard']
  | components['schemas']['PolicyKnowledgeCard']
  | components['schemas']['DomainTermKnowledgeCard']
export type KnowledgeCardInput = components['schemas']['ScreenKnowledgeCardInput']
  | components['schemas']['FlowKnowledgeCardInput']
  | components['schemas']['AssertionKnowledgeCardInput']
  | components['schemas']['IssueKnowledgeCardInput']
  | components['schemas']['DataKnowledgeCardInput']
  | components['schemas']['PolicyKnowledgeCardInput']
  | components['schemas']['DomainTermKnowledgeCardInput']
export type KnowledgeCandidateDraft = components['schemas']['ScreenKnowledgeCandidateDraft']
  | components['schemas']['FlowKnowledgeCandidateDraft']
  | components['schemas']['AssertionKnowledgeCandidateDraft']
  | components['schemas']['IssueKnowledgeCandidateDraft']
  | components['schemas']['DataKnowledgeCandidateDraft']
  | components['schemas']['PolicyKnowledgeCandidateDraft']
  | components['schemas']['DomainTermKnowledgeCandidateDraft']
export type KnowledgeCandidateRecord = components['schemas']['KnowledgeCandidateRecord']
export type KnowledgeCandidateListData = components['schemas']['KnowledgeCandidateListData']
export type KnowledgeCandidateDecisionRequest = components['schemas']['KnowledgeCandidateDecisionRequest']
export type KnowledgeCandidateApproveData = components['schemas']['KnowledgeCandidateApproveData']
export type KnowledgeCandidateRejectData = components['schemas']['KnowledgeCandidateRejectData']
export type KnowledgeCardListData = components['schemas']['KnowledgeCardListData']
export type KnowledgeCardGetData = components['schemas']['KnowledgeCardGetData']
export type KnowledgeCardMutationData = components['schemas']['KnowledgeCardMutationData']
export type KnowledgeCardDeleteData = components['schemas']['KnowledgeCardDeleteData']
export type KnowledgeCardType = KnowledgeCandidateDraft['card_type']
export type KnowledgeCardStatus = KnowledgeCard['status']
export type KnowledgeSourceKind = KnowledgeSource['kind']
export type KnowledgeCandidateStatus = KnowledgeCandidateRecord['status']

export async function listKnowledgeCandidates(input: {
  appId: string
  status?: KnowledgeCandidateStatus
  limit?: number
}): Promise<KnowledgeCandidateListData> {
  return unwrapData<components['schemas']['SuccessResponse_KnowledgeCandidateListData_']>(
    client.GET('/v1/apps/{app_id}/knowledge/candidates', {
      params: {
        path: {
          app_id: input.appId,
        },
        query: {
          status: input.status ?? undefined,
          limit: input.limit ?? 50,
        },
      },
    })
  )
}

export async function approveKnowledgeCandidate(input: {
  appId: string
  candidateId: string
  request?: KnowledgeCandidateDecisionRequest
}): Promise<KnowledgeCandidateApproveData> {
  return unwrapData<components['schemas']['SuccessResponse_KnowledgeCandidateApproveData_']>(
    client.POST('/v1/apps/{app_id}/knowledge/candidates/{candidate_id}/approve', {
      params: {
        path: {
          app_id: input.appId,
          candidate_id: input.candidateId,
        },
      },
      body: {
        reviewed_by: input.request?.reviewed_by ?? null,
        review_note: input.request?.review_note ?? null,
      },
    })
  )
}

export async function rejectKnowledgeCandidate(input: {
  appId: string
  candidateId: string
  request?: KnowledgeCandidateDecisionRequest
}): Promise<KnowledgeCandidateRejectData> {
  return unwrapData<components['schemas']['SuccessResponse_KnowledgeCandidateRejectData_']>(
    client.POST('/v1/apps/{app_id}/knowledge/candidates/{candidate_id}/reject', {
      params: {
        path: {
          app_id: input.appId,
          candidate_id: input.candidateId,
        },
      },
      body: {
        reviewed_by: input.request?.reviewed_by ?? null,
        review_note: input.request?.review_note ?? null,
      },
    })
  )
}

export async function listKnowledgeCards(input: {
  appId: string
  query?: string
  cardType?: KnowledgeCardType
  status?: KnowledgeCardStatus
  limit?: number
  offset?: number
}): Promise<KnowledgeCardListData> {
  return unwrapData<components['schemas']['SuccessResponse_KnowledgeCardListData_']>(
    client.GET('/v1/apps/{app_id}/knowledge/cards', {
      params: {
        path: {
          app_id: input.appId,
        },
        query: {
          q: input.query ?? undefined,
          card_type: input.cardType ?? undefined,
          status: input.status ?? undefined,
          limit: input.limit ?? 50,
          offset: input.offset ?? 0,
        },
      },
    })
  )
}

export async function getKnowledgeCard(input: {
  appId: string
  cardId: string
}): Promise<KnowledgeCardGetData> {
  return unwrapData<components['schemas']['SuccessResponse_KnowledgeCardGetData_']>(
    client.GET('/v1/apps/{app_id}/knowledge/cards/{card_id}', {
      params: {
        path: {
          app_id: input.appId,
          card_id: input.cardId,
        },
      },
    })
  )
}

export async function createKnowledgeCard(input: {
  appId: string
  card: KnowledgeCardInput
}): Promise<KnowledgeCardMutationData> {
  return unwrapData<components['schemas']['SuccessResponse_KnowledgeCardMutationData_']>(
    client.POST('/v1/apps/{app_id}/knowledge/cards', {
      params: {
        path: {
          app_id: input.appId,
        },
      },
      body: {
        card: input.card,
      },
    })
  )
}

export async function updateKnowledgeCard(input: {
  appId: string
  cardId: string
  card: KnowledgeCardInput
}): Promise<KnowledgeCardMutationData> {
  return unwrapData<components['schemas']['SuccessResponse_KnowledgeCardMutationData_']>(
    client.PUT('/v1/apps/{app_id}/knowledge/cards/{card_id}', {
      params: {
        path: {
          app_id: input.appId,
          card_id: input.cardId,
        },
      },
      body: {
        card: input.card,
      },
    })
  )
}

export async function deleteKnowledgeCard(input: {
  appId: string
  cardId: string
}): Promise<KnowledgeCardDeleteData> {
  return unwrapData<components['schemas']['SuccessResponse_KnowledgeCardDeleteData_']>(
    client.DELETE('/v1/apps/{app_id}/knowledge/cards/{card_id}', {
      params: {
        path: {
          app_id: input.appId,
          card_id: input.cardId,
        },
      },
    })
  )
}
