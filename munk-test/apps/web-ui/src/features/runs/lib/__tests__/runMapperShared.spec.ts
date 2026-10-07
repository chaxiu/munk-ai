import { describe, expect, it } from 'vitest'

import { isCancelInProgress, isTerminalStatus, statusTone } from '@/features/runs/lib/runMapperShared'

describe('runMapperShared status helpers', () => {
  it('treats interrupted as terminal', () => {
    expect(isTerminalStatus('interrupted')).toBe(true)
    expect(isTerminalStatus('running')).toBe(false)
  })

  it('detects cancel in progress for running operations', () => {
    expect(isCancelInProgress({ status: 'running', cancel_requested: true })).toBe(true)
    expect(isCancelInProgress({ status: 'cancelled', cancel_requested: true })).toBe(false)
    expect(isCancelInProgress({ status: 'running', cancel_requested: false })).toBe(false)
  })

  it('uses warning tone for interrupted', () => {
    expect(statusTone('interrupted')).toBe('warning')
  })
})
