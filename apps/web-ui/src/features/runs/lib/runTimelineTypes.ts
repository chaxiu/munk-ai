import type { OperationEventsData } from '@/shared/api/operations'

export type OperationEventItem = NonNullable<OperationEventsData['items']>[number]

export type RunTimelineDetailRow = {
  label: string
  value: string
}

export type RunTimelineSetupSection = {
  id: string
  label: string
  previewText: string
  fullText: string
}

export type RunTimelineEventView = {
  kind: 'default' | 'llm' | 'setup_step' | 'start_state_step'
  title: string
  description: string | null
  category: 'orchestration' | 'runtime'
  categoryLabel: string
  roleLabel: string | null
  scopeLabel: string | null
  phaseLabel: string | null
  attemptLabel: string | null
  eventTypeLabel: string
  rawData: Record<string, unknown> | null
  detailRows: RunTimelineDetailRow[]
  failed?: boolean
  skipped?: boolean
  llmPreviewText?: string | null
  llmFullText?: string | null
  llmRequestId?: string | null
  llmProvider?: string | null
  llmModel?: string | null
  llmStatusCode?: number | null
  setupSections?: RunTimelineSetupSection[]
  startStateSections?: RunTimelineSetupSection[]
  defaultExpandedSectionIds?: string[]
}
