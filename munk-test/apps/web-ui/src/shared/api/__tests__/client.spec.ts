import { describe, expect, it } from 'vitest'

import { LocalApiClientError, unwrapData } from '../client'

describe('unwrapData', () => {
  it('returns data payload for successful responses', async () => {
    const payload = await unwrapData(Promise.resolve({
      data: {
        data: {
          operation_id: 'op-1'
        }
      },
      response: new Response(null, { status: 200 })
    }))

    expect(payload).toEqual({ operation_id: 'op-1' })
  })

  it('maps api error envelopes to LocalApiClientError', async () => {
    await expect(() => unwrapData(Promise.resolve({
      error: {
        ok: false,
        command: 'recordings_get',
        error: {
          code: 'recording_session_not_found',
          message: 'missing',
          details: {
            recording_id: 'rec-1'
          }
        }
      },
      response: new Response(null, { status: 404, statusText: 'Not Found' })
    }))).rejects.toMatchObject({
      name: 'LocalApiClientError',
      code: 'recording_session_not_found',
      message: 'missing',
      status: 404
    })
  })

  it('maps non-envelope failures to a generic client error', async () => {
    await expect(() => unwrapData(Promise.resolve({
      error: {
        unexpected: true
      },
      response: new Response(null, { status: 500, statusText: 'Internal Server Error' })
    }))).rejects.toBeInstanceOf(LocalApiClientError)
  })
})
