const PLAN_SOURCE_LABEL_KEYS: Record<string, string> = {
  pydantic_plan_agent: 'tests.sources.pydantic_plan_agent',
  change_verification: 'tests.sources.change_verification',
  change_driven_plan_agent: 'tests.sources.change_driven_plan_agent',
  recording_export: 'tests.sources.recording_export',
  plan_import: 'tests.sources.plan_import',
}

type Translate = (key: string) => string

export function formatPlanSourceLabel(
  source: string | null | undefined,
  t: Translate
): string {
  if (!source) {
    return ''
  }
  const labelKey = PLAN_SOURCE_LABEL_KEYS[source]
  return labelKey ? t(labelKey) : source
}
