import { describe, expect, it } from 'vitest'

import {
  buildSetupStepPayload,
  buildSetupStepsPayload,
  createSetupStepForm,
  httpMethodSupportsBody,
} from '../setupStepForm'

describe('setupStepForm', () => {
  it('round-trips an http setup step', () => {
    const payload = {
      kind: 'http' as const,
      base: 'test_backend',
      method: 'POST' as const,
      path: '/api/seed',
      headers: { 'X-Trace': 'abc' },
      query: { page: '1' },
      body: { count: 2 },
      expected_status: [200, 201],
    }

    const form = createSetupStepForm(payload)
    expect(buildSetupStepPayload(form)).toEqual(payload)
  })

  it('round-trips a command setup step', () => {
    const payload = {
      kind: 'command' as const,
      exec: 'echo',
      args: ['ready'],
      expected_exit_code: 0,
    }

    const form = createSetupStepForm(payload)
    expect(buildSetupStepPayload(form)).toEqual(payload)
  })

  it('rejects duplicate header keys', () => {
    expect(() => buildSetupStepsPayload([
      {
        kind: 'http',
        base: 'test_backend',
        method: 'GET',
        path: '/',
        headers: [
          { key: 'X-Trace', value: 'a' },
          { key: 'X-Trace', value: 'b' },
        ],
        query: [],
        body_json: '',
        expected_status_text: '200',
      },
    ])).toThrow(/duplicate key/)
  })

  it('drops empty header rows and rejects body on GET', () => {
    expect(buildSetupStepPayload({
      kind: 'http',
      base: 'test_backend',
      method: 'GET',
      path: '/',
      headers: [{ key: '', value: 'ignored' }, { key: 'X-Trace', value: 'abc' }],
      query: [],
      body_json: '',
      expected_status_text: '200',
    })).toEqual({
      kind: 'http',
      base: 'test_backend',
      method: 'GET',
      path: '/',
      headers: { 'X-Trace': 'abc' },
      query: {},
      body: null,
      expected_status: [200],
    })

    expect(() => buildSetupStepPayload({
      kind: 'http',
      base: 'test_backend',
      method: 'GET',
      path: '/',
      headers: [],
      query: [],
      body_json: '{"count":1}',
      expected_status_text: '200',
    })).toThrow(/only supported for POST, PUT, and PATCH/)
  })

  it('identifies body-capable methods', () => {
    expect(httpMethodSupportsBody('POST')).toBe(true)
    expect(httpMethodSupportsBody('GET')).toBe(false)
  })
})
