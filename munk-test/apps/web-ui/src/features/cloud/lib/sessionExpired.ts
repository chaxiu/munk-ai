import { LocalApiClientError } from '@/shared/api/client'

export function isCloudSessionExpiredError(error: unknown): boolean {
  return error instanceof LocalApiClientError && error.code === 'session_expired'
}
