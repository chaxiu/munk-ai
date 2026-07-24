import type { Translate } from './runMapperShared'
import type { OperationEventItem, RunTimelineEventView } from './runTimelineTypes'
import { asObject } from './runMapperShared'
import { presentCanonicalRunTimelineEvent, hasCanonicalTimelineFields } from './runTimelineCanonical'
import { presentHistoricalRunTimelineEvent } from './runTimelineHistorical'
import { presentLlmRunTimelineEvent } from './runTimelineLlm'
import { presentSetupStepRunTimelineEvent } from './runTimelineSetup'
import { presentStartStateStepRunTimelineEvent } from './runTimelineStartState'
import { LLM_TIMELINE_EVENT_TYPES, SETUP_STEP_EVENT_TYPE, START_STATE_STEP_EVENT_TYPE } from './runTimelineShared'

export type { RunTimelineEventView } from './runTimelineTypes'

export function presentRunTimelineEvent(item: OperationEventItem, t: Translate): RunTimelineEventView {
  if (LLM_TIMELINE_EVENT_TYPES.has(item.event_type)) {
    return presentLlmRunTimelineEvent(item, t)
  }

  if (item.event_type === SETUP_STEP_EVENT_TYPE) {
    return presentSetupStepRunTimelineEvent(item, t)
  }

  if (item.event_type === START_STATE_STEP_EVENT_TYPE) {
    return presentStartStateStepRunTimelineEvent(item, t)
  }

  const data = asObject(item.data_json)
  if (!hasCanonicalTimelineFields(item)) {
    return presentHistoricalRunTimelineEvent(item, data, t)
  }

  return presentCanonicalRunTimelineEvent(item, t)
}
