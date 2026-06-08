import type { components } from '../contracts/generated/local-api'
import { client, unwrapData } from './client'

export type PlanCliRequest = components['schemas']['PlanCliRequest']
export type RunCaseCliRequest = components['schemas']['RunCaseCliRequest']
export type RunPlanCliRequest = components['schemas']['RunPlanCliRequest'] & {
  device_ref?: string | null
}
export type RunPlansCliRequest = components['schemas']['RunPlansCliRequest']
export type ReviewCliRequest = components['schemas']['ReviewCliRequest']
export type VerifyChangeCliRequest = components['schemas']['VerifyChangeCliRequest']
export type OperationSubmissionData = components['schemas']['OperationSubmissionData']

interface SubmitOptions {
  wait?: boolean
  detach?: boolean
}

function submitParams(options?: SubmitOptions) {
  return {
    query: {
      wait: options?.wait ?? true,
      detach: options?.detach ?? false
    }
  }
}

export async function submitPlan(
  request: PlanCliRequest,
  options?: SubmitOptions
): Promise<OperationSubmissionData> {
  return unwrapData<components['schemas']['SuccessResponse_OperationSubmissionData_']>(
    client.POST('/v1/plan', {
      params: submitParams(options),
      body: request
    })
  )
}

export async function submitRunCase(
  request: RunCaseCliRequest,
  options?: SubmitOptions
): Promise<OperationSubmissionData> {
  return unwrapData<components['schemas']['SuccessResponse_OperationSubmissionData_']>(
    client.POST('/v1/run/case', {
      params: submitParams(options),
      body: request
    })
  )
}

export async function submitRunPlan(
  request: RunPlanCliRequest,
  options?: SubmitOptions
): Promise<OperationSubmissionData> {
  return unwrapData<components['schemas']['SuccessResponse_OperationSubmissionData_']>(
    client.POST('/v1/run/plan', {
      params: submitParams(options),
      body: request
    })
  )
}

export async function submitRunPlans(
  request: RunPlansCliRequest,
  options?: SubmitOptions
): Promise<OperationSubmissionData> {
  return unwrapData<components['schemas']['SuccessResponse_OperationSubmissionData_']>(
    client.POST('/v1/run/plans', {
      params: submitParams(options),
      body: request
    })
  )
}

export async function submitVerifyChange(
  request: VerifyChangeCliRequest,
  options?: SubmitOptions
): Promise<OperationSubmissionData> {
  return unwrapData<components['schemas']['SuccessResponse_OperationSubmissionData_']>(
    client.POST('/v1/verify/change', {
      params: submitParams(options),
      body: request
    })
  )
}

export async function submitReview(
  request: ReviewCliRequest,
  options?: SubmitOptions
): Promise<OperationSubmissionData> {
  return unwrapData<components['schemas']['SuccessResponse_OperationSubmissionData_']>(
    client.POST('/v1/review', {
      params: submitParams(options),
      body: request
    })
  )
}
