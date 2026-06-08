import { describe, expect, it } from 'vitest'

import { DEFAULT_POLL_INTERVAL_MS } from '@/shared/query/defaults'
import { hasActiveRuns, runsRefetchInterval } from '../queries/useRunsQuery'

describe('useRunsQuery polling helpers', () => {
  it('detects queued and running runs as active', () => {
    expect(hasActiveRuns([{ status: 'queued' }])).toBe(true)
    expect(hasActiveRuns([{ status: 'running' }])).toBe(true)
  })

  it('treats terminal-only runs as inactive', () => {
    expect(hasActiveRuns([
      { status: 'succeeded' },
      { status: 'failed' },
      { status: 'cancelled' },
    ])).toBe(false)
  })

  it('returns the shared poll interval only for the first page with active runs', () => {
    expect(runsRefetchInterval({ items: [{ status: 'running' }], offset: 0 })).toBe(DEFAULT_POLL_INTERVAL_MS)
    expect(runsRefetchInterval({ items: [{ status: 'queued' }], offset: 0 })).toBe(DEFAULT_POLL_INTERVAL_MS)
    expect(runsRefetchInterval({ items: [{ status: 'running' }], offset: 20 })).toBe(false)
    expect(runsRefetchInterval({ items: [{ status: 'succeeded' }], offset: 0 })).toBe(false)
    expect(runsRefetchInterval({ items: [], offset: 0 })).toBe(false)
    expect(runsRefetchInterval()).toBe(false)
  })
})
