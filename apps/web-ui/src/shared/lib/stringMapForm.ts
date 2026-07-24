export type StringMapEntry = {
  key: string
  value: string
}

export function createEmptyStringMapEntry(): StringMapEntry {
  return { key: '', value: '' }
}

export function recordToStringMapEntries(record: Record<string, string> | undefined | null): StringMapEntry[] {
  if (!record) {
    return []
  }
  return Object.entries(record).map(([key, value]) => ({ key, value }))
}

export function stringMapEntriesToRecord(
  entries: StringMapEntry[],
  fieldName: string,
): Record<string, string> {
  const result: Record<string, string> = {}
  const seenKeys = new Set<string>()

  for (const [index, entry] of entries.entries()) {
    const key = entry.key.trim()
    if (!key) {
      continue
    }
    if (seenKeys.has(key)) {
      throw new Error(`${fieldName} has duplicate key: ${key}`)
    }
    seenKeys.add(key)
    result[key] = entry.value
  }

  return result
}
