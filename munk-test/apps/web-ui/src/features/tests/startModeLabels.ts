const START_MODE_LABEL_KEYS: Record<string, string> = {
  reset: 'tests.startModes.reset',
  resume: 'tests.startModes.resume',
}

type Translate = (key: string) => string

export function formatStartModeLabel(
  startMode: string | null | undefined,
  t: Translate
): string {
  if (!startMode) {
    return ''
  }
  const labelKey = START_MODE_LABEL_KEYS[startMode]
  return labelKey ? t(labelKey) : startMode
}
