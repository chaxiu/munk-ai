import type { TestCasePayload } from '@/shared/api/tests'
import {
  recordToStringMapEntries,
  stringMapEntriesToRecord,
  type StringMapEntry,
} from '@/shared/lib/stringMapForm'

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

export type SetupStepKind = 'http' | 'command'

export type HttpSetupStepForm = {
  kind: 'http'
  base: string
  method: HttpMethod
  path: string
  headers: StringMapEntry[]
  query: StringMapEntry[]
  body_json: string
  expected_status_text: string
}

export type CommandSetupStepForm = {
  kind: 'command'
  exec: string
  args_text: string
  expected_exit_code: string
}

export type SetupStepForm = HttpSetupStepForm | CommandSetupStepForm

export type SetupStepPayload = NonNullable<TestCasePayload['setup']>[number]

const BODY_SUPPORTED_METHODS = new Set<HttpMethod>(['POST', 'PUT', 'PATCH'])

export function httpMethodSupportsBody(method: HttpMethod): boolean {
  return BODY_SUPPORTED_METHODS.has(method)
}

export function createEmptyHttpSetupStepForm(): HttpSetupStepForm {
  return {
    kind: 'http',
    base: '',
    method: 'GET',
    path: '/',
    headers: [],
    query: [],
    body_json: '',
    expected_status_text: '200',
  }
}

export function createEmptyCommandSetupStepForm(): CommandSetupStepForm {
  return {
    kind: 'command',
    exec: '',
    args_text: '',
    expected_exit_code: '0',
  }
}

export function createSetupStepForm(step: SetupStepPayload): SetupStepForm {
  if (step.kind === 'http') {
    return {
      kind: 'http',
      base: step.base ?? '',
      method: step.method ?? 'GET',
      path: step.path ?? '/',
      headers: recordToStringMapEntries(step.headers ?? {}),
      query: recordToStringMapEntries(step.query ?? {}),
      body_json: step.body === null || step.body === undefined ? '' : JSON.stringify(step.body, null, 2),
      expected_status_text: formatStatusList(step.expected_status ?? [200]),
    }
  }
  return {
    kind: 'command',
    exec: step.exec ?? '',
    args_text: formatLineList(step.args ?? []),
    expected_exit_code: String(step.expected_exit_code ?? 0),
  }
}

export function buildSetupStepPayload(form: SetupStepForm): SetupStepPayload {
  if (form.kind === 'http') {
    const base = form.base.trim()
    if (!base) {
      throw new Error('setup http base must not be empty')
    }
    const body = httpMethodSupportsBody(form.method)
      ? parseOptionalJsonValue(form.body_json, 'setup body')
      : null
    if (!httpMethodSupportsBody(form.method) && form.body_json.trim()) {
      throw new Error(`setup body is only supported for POST, PUT, and PATCH`)
    }
    return {
      kind: 'http',
      base,
      method: form.method,
      path: normalizePath(form.path),
      headers: stringMapEntriesToRecord(form.headers, 'setup headers'),
      query: stringMapEntriesToRecord(form.query, 'setup query'),
      body,
      expected_status: parseStatusList(form.expected_status_text),
    }
  }
  const exec = form.exec.trim()
  if (!exec) {
    throw new Error('setup command exec must not be empty')
  }
  return {
    kind: 'command',
    exec,
    args: parseLineList(form.args_text),
    expected_exit_code: parseInteger(form.expected_exit_code, 'expected_exit_code'),
  }
}

export function buildSetupStepsPayload(forms: SetupStepForm[]): SetupStepPayload[] {
  return forms.map((form, index) => {
    try {
      return buildSetupStepPayload(form)
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      throw new Error(`setup step ${index + 1}: ${message}`)
    }
  })
}

function normalizePath(value: string): string {
  const trimmed = value.trim()
  if (!trimmed) {
    return '/'
  }
  return trimmed.startsWith('/') ? trimmed : `/${trimmed}`
}

function formatLineList(values: string[]): string {
  return values.join('\n')
}

function formatStatusList(values: number[]): string {
  return values.join(', ')
}

function parseLineList(value: string): string[] {
  return value
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean)
}

function parseOptionalJsonValue(value: string, fieldName: string): unknown | null {
  const trimmed = value.trim()
  if (!trimmed) {
    return null
  }
  try {
    return JSON.parse(trimmed) as unknown
  } catch {
    throw new Error(`${fieldName} must be valid JSON`)
  }
}

function parseStatusList(value: string): number[] {
  const trimmed = value.trim()
  if (!trimmed) {
    return [200]
  }
  const items = trimmed.split(/[\n,]/).map((item) => item.trim()).filter(Boolean)
  if (!items.length) {
    return [200]
  }
  return items.map((item) => parseInteger(item, 'expected_status'))
}

function parseInteger(value: string, fieldName: string): number {
  const trimmed = value.trim()
  if (!/^-?\d+$/.test(trimmed)) {
    throw new Error(`${fieldName} must be an integer`)
  }
  return Number.parseInt(trimmed, 10)
}
