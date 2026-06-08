import { LocalApiClientError } from '@/shared/api/client'

export function getQueryErrorMessage(error: unknown): string {
  if (error instanceof LocalApiClientError) {
    return error.code || error.message
  }
  if (error instanceof Error) {
    return error.message
  }
  return String(error)
}
