export function formatPlanVersionLabel(version: string | null | undefined): string {
  const cleaned = String(version ?? '').trim()
  if (!cleaned) {
    return '-'
  }

  const legacyMatch = /^phase[0-9a-z]+\.v(\d+)$/i.exec(cleaned)
  if (legacyMatch) {
    return `v${legacyMatch[1]}.0`
  }

  const shortMatch = /^v(\d+)$/i.exec(cleaned)
  if (shortMatch) {
    return `v${shortMatch[1]}.0`
  }

  return cleaned
}
