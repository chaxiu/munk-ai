import { describe, expect, it } from 'vitest'

import {
  recordToStringMapEntries,
  stringMapEntriesToRecord,
} from '@/shared/lib/stringMapForm'

describe('stringMapForm', () => {
  it('converts records to editable entries', () => {
    expect(recordToStringMapEntries({ page: '1', q: 'abc' })).toEqual([
      { key: 'page', value: '1' },
      { key: 'q', value: 'abc' },
    ])
  })

  it('drops blank keys and rejects duplicates', () => {
    expect(stringMapEntriesToRecord([
      { key: 'page', value: '1' },
      { key: '', value: 'ignored' },
    ], 'query')).toEqual({ page: '1' })

    expect(() => stringMapEntriesToRecord([
      { key: 'page', value: '1' },
      { key: 'page', value: '2' },
    ], 'query')).toThrow(/duplicate key/)
  })
})
