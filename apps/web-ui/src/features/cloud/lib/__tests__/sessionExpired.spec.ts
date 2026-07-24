import { describe, expect, it } from 'vitest'

import { isCloudSessionExpiredError } from '../sessionExpired'
import { LocalApiClientError } from '@/shared/api/client'

describe('isCloudSessionExpiredError', () => {
  it('matches session_expired LocalApiClientError', () => {
    expect(
      isCloudSessionExpiredError(
        new LocalApiClientError({
          message: 'Cloud session expired. Sign in again to continue.',
          code: 'session_expired',
          status: 401,
        }),
      ),
    ).toBe(true)
  })

  it('ignores other errors', () => {
    expect(
      isCloudSessionExpiredError(
        new LocalApiClientError({
          message: 'Not signed in',
          code: 'not_authenticated',
          status: 401,
        }),
      ),
    ).toBe(false)
    expect(isCloudSessionExpiredError(new Error('boom'))).toBe(false)
    expect(isCloudSessionExpiredError(null)).toBe(false)
  })
})
