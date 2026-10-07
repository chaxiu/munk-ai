import createClient from 'openapi-fetch'

import type { components, paths } from '../contracts/generated/local-api'
import { logger } from '@/shared/logging/logger'

type ApiErrorResponse = components['schemas']['ErrorResponse']

export class LocalApiClientError extends Error {
  code: string
  details?: Record<string, unknown>
  status: number

  constructor(input: {
    message: string
    code?: string
    details?: Record<string, unknown>
    status: number
  }) {
    super(input.message)
    this.name = 'LocalApiClientError'
    this.code = input.code ?? 'request_failed'
    this.details = input.details
    this.status = input.status
  }
}

const client = createClient<paths>({
  baseUrl: ''
})

function isApiErrorResponse(value: unknown): value is ApiErrorResponse {
  if (!value || typeof value !== 'object') {
    return false
  }
  const maybeError = value as Record<string, unknown>
  if (maybeError.ok !== false || typeof maybeError.command !== 'string') {
    return false
  }
  const error = maybeError.error
  if (!error || typeof error !== 'object') {
    return false
  }
  return typeof (error as Record<string, unknown>).message === 'string'
}

function buildClientError(response: Response, error: unknown): LocalApiClientError {
  if (isApiErrorResponse(error)) {
    return new LocalApiClientError({
      message: error.error.message,
      code: error.error.code,
      details: error.error.details ?? undefined,
      status: response.status
    })
  }
  return new LocalApiClientError({
    message: response.statusText || `request failed: ${response.status}`,
    status: response.status
  })
}

export async function unwrapData<TEnvelope extends { data: unknown }>(
  promise: Promise<{
    data?: TEnvelope
    error?: unknown
    response: Response
  }>
): Promise<TEnvelope['data']> {
  const startedAt = performance.now()
  const { data, error, response } = await promise
  if (data) {
    logger.debug({
      scope: 'api',
      event: 'request.success',
      message: `Local API request succeeded: ${response.url || 'unknown'}`,
      context: {
        status: response.status,
        durationMs: Math.round(performance.now() - startedAt),
      },
    })
    return data.data
  }
  const clientError = buildClientError(response, error)
  logger.error({
    scope: 'api',
    event: 'request.error',
    message: clientError.message,
    context: {
      status: clientError.status,
      code: clientError.code,
      durationMs: Math.round(performance.now() - startedAt),
      url: response.url || 'unknown',
    },
  })
  throw clientError
}

export { client }
