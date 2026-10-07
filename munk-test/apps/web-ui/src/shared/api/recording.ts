import type { components } from '../contracts/generated/local-api'
import { client, unwrapData } from './client'
import type { InteractionPayload } from './recording.types'

type ApiRecordingSession = components['schemas']['RecordingSession']
type ApiRecordedInputEvent = components['schemas']['RecordedInputEvent']
type ApiTimelineEntry = components['schemas']['TimelineEntry']
export type ForwardingAckRequest = components['schemas']['ForwardingAckRequest']

export interface RecordingSession {
  recording_id: string
  app_id: string
  case_id: string | null
  entry_identity: string | null
  device_ref: string | null
  status: string
  asset_dir: string
  created_at: string
  started_at: string | null
  finished_at: string | null
  latest_frame_seq: number | null
  failure_reason: string | null
}

export interface RecordedInputEvent {
  event_id: string
  recording_id: string
  kind: 'click' | 'swipe' | 'input' | 'back'
  timestamp: string
  summary: string | null
  source?: string
  payload: Record<string, unknown>
}

export interface TimelineEntry {
  entry_id: string
  recording_id: string
  seq: number
  kind: 'click' | 'swipe' | 'input' | 'back'
  timestamp: string
  summary: string | null
  forwarding_event_id: string
  recording_event_id: string
  before_observation_id: string
  after_observation_id: string
  after_stabilized: boolean
}

export type ObservationSnapshot = components['schemas']['ObservationSnapshot']
export type RecordingAnalysisResult = components['schemas']['RecordingAnalysisResult']
export type RecordingCaseExport = components['schemas']['RecordingCaseExport']
export type RecordingReplayResult = components['schemas']['RecordingReplayResult']
export interface DeviceDescriptor {
  platform: string
  device_ref: string
  display_name: string
  kind: string
  availability: string
  is_booted: boolean | null
  raw: Record<string, unknown>
}
export interface RecordingBridgeInfo {
  recording_id: string
  base_url: string
  ws_url: string
}

export interface RecordingCreateData {
  session: RecordingSession
}

export interface RecordingBeginData {
  session: RecordingSession
  bridge: RecordingBridgeInfo
}

export interface RecordingGetData {
  session: RecordingSession
  events: RecordedInputEvent[]
  timeline: TimelineEntry[]
}

export interface RecordingTapData {
  event: RecordedInputEvent
}

export interface RecordingInteractionData {
  entry: TimelineEntry
}

export interface RecordingTimelineData {
  timeline: TimelineEntry[]
}

export interface RecordingObservationData {
  observation: ObservationSnapshot
}

export interface RecordingAnalysisData {
  analysis: RecordingAnalysisResult
}

export interface RecordingAnalysisSubmissionData {
  operation_id: string
  status: string
  app_id?: string | null
  phase?: string | null
}

export interface RecordingExportData {
  analysis: RecordingAnalysisResult
  case: RecordingCaseExport
  artifacts: Record<string, string>
}

export interface RecordingReplayData {
  replay: RecordingReplayResult
}

export interface RecordingSessionData {
  session: RecordingSession
}

function requireField<T>(value: T | undefined, field: string): T {
  if (value === undefined) {
    throw new Error(`invalid Local API response: missing ${field}`)
  }
  return value
}

function normalizeSession(session: ApiRecordingSession): RecordingSession {
  const extendedSession = session as ApiRecordingSession & {
    app_target?: { entry_identity?: string | null } | null
    device_ref?: string | null
  }
  return {
    recording_id: requireField(session.recording_id, 'session.recording_id'),
    app_id: requireField(session.app_id, 'session.app_id'),
    case_id: session.case_id ?? null,
    entry_identity: extendedSession.app_target?.entry_identity ?? null,
    device_ref: extendedSession.device_ref ?? null,
    status: session.status,
    asset_dir: requireField(session.asset_dir, 'session.asset_dir'),
    created_at: requireField(session.created_at, 'session.created_at'),
    started_at: session.started_at ?? null,
    finished_at: session.finished_at ?? null,
    latest_frame_seq: session.latest_frame_seq ?? null,
    failure_reason: session.failure_reason ?? null
  }
}

function normalizeEvent(event: ApiRecordedInputEvent): RecordedInputEvent {
  return {
    event_id: requireField(event.event_id, 'event.event_id'),
    recording_id: requireField(event.recording_id, 'event.recording_id'),
    kind: event.kind,
    timestamp: requireField(event.timestamp, 'event.timestamp'),
    summary: event.summary ?? null,
    source: event.source,
    payload: event.payload ?? {}
  }
}

function normalizeTimelineEntry(entry: ApiTimelineEntry): TimelineEntry {
  return {
    entry_id: requireField(entry.entry_id, 'timeline.entry_id'),
    recording_id: requireField(entry.recording_id, 'timeline.recording_id'),
    seq: entry.seq,
    kind: entry.kind,
    timestamp: requireField(entry.timestamp, 'timeline.timestamp'),
    summary: entry.summary ?? null,
    forwarding_event_id: requireField(entry.forwarding_event_id, 'timeline.forwarding_event_id'),
    recording_event_id: requireField(entry.recording_event_id, 'timeline.recording_event_id'),
    before_observation_id: requireField(entry.before_observation_id, 'timeline.before_observation_id'),
    after_observation_id: requireField(entry.after_observation_id, 'timeline.after_observation_id'),
    after_stabilized: entry.after_stabilized
  }
}

function normalizeBridgeInfo(bridge: components['schemas']['RecordingBridgeInfo']): RecordingBridgeInfo {
  return {
    recording_id: requireField(bridge.recording_id, 'bridge.recording_id'),
    base_url: requireField(bridge.base_url, 'bridge.base_url'),
    ws_url: requireField(bridge.ws_url, 'bridge.ws_url')
  }
}

function normalizeDeviceDescriptor(
  device: Partial<DeviceDescriptor> & {
    device_ref?: string
    display_name?: string
    kind?: string
    availability?: string
  }
): DeviceDescriptor {
  return {
    platform: device.platform ?? 'ios',
    device_ref: requireField(device.device_ref, 'device.device_ref'),
    display_name: requireField(device.display_name, 'device.display_name'),
    kind: requireField(device.kind, 'device.kind'),
    availability: requireField(device.availability, 'device.availability'),
    is_booted: device.is_booted ?? null,
    raw: device.raw ?? {}
  }
}

function normalizeInteractionPayload(payload: InteractionPayload): Record<string, unknown> {
  if (payload.kind === 'click') {
    return {
      x: payload.x,
      y: payload.y,
      width: payload.width,
      height: payload.height
    }
  }
  if (payload.kind === 'swipe') {
    return {
      start_x: payload.startX,
      start_y: payload.startY,
      end_x: payload.endX,
      end_y: payload.endY,
      width: payload.width,
      height: payload.height,
      duration_ms: payload.durationMs
    }
  }
  if (payload.kind === 'input') {
    return {
      text: payload.text,
      submit: payload.submit === true
    }
  }
  return {}
}

export async function createRecordingSession(input: {
  appId: string
  entryIdentity: string
  deviceRef?: string
  caseId?: string
}): Promise<RecordingCreateData> {
  const data = await unwrapData<components['schemas']['SuccessResponse_RecordingCreateData_']>(
    client.POST('/v1/recordings', {
      body: {
        app_target: {
          app_id: input.appId,
          platform: 'android',
          android: {
            package_name: input.entryIdentity
          }
        },
        device_ref: input.deviceRef,
        case_id: input.caseId
      } as never
    })
  )
  return {
    session: normalizeSession(data.session)
  }
}

export async function beginRecordingSession(recordingId: string): Promise<RecordingBeginData> {
  const data = await unwrapData<components['schemas']['SuccessResponse_RecordingBeginData_']>(
    client.POST('/v1/recordings/{recording_id}/begin', {
      params: {
        path: {
          recording_id: recordingId
        }
      }
    })
  )
  return {
    session: normalizeSession(data.session),
    bridge: normalizeBridgeInfo(data.bridge)
  }
}

export async function getRecordingSession(recordingId: string): Promise<RecordingGetData> {
  const data = await unwrapData<components['schemas']['SuccessResponse_RecordingGetData_']>(
    client.GET('/v1/recordings/{recording_id}', {
      params: {
        path: {
          recording_id: recordingId
        }
      }
    })
  )
  return {
    session: normalizeSession(data.session),
    events: (data.events ?? []).map(normalizeEvent),
    timeline: (data.timeline ?? []).map(normalizeTimelineEntry)
  }
}

export async function listDevices(platform?: string): Promise<DeviceDescriptor[]> {
  const data = await unwrapData<{ data: { items?: Array<Partial<DeviceDescriptor>> } }>(
    client.GET('/v1/devices' as never, {
      params: {
        query: {
          platform
        }
      }
    } as never) as never
  )
  return (data.items ?? []).map(normalizeDeviceDescriptor)
}

export async function observeTapEvent(
  recordingId: string,
  payload: { x: number, y: number, width: number, height: number }
): Promise<RecordingTapData> {
  const data = await unwrapData<components['schemas']['SuccessResponse_RecordingTapData_']>(
    client.POST('/v1/recordings/{recording_id}/events/tap', {
      params: {
        path: {
          recording_id: recordingId
        }
      },
      body: {
        ...payload,
        source: 'scrcpy_bridge'
      }
    })
  )
  return {
    event: normalizeEvent(data.event)
  }
}

export async function recordInteraction(
  recordingId: string,
  payload: InteractionPayload,
  forwardingAck: ForwardingAckRequest
): Promise<RecordingInteractionData> {
  const data = await unwrapData<components['schemas']['SuccessResponse_RecordingInteractionData_']>(
    client.POST('/v1/recordings/{recording_id}/events', {
      params: {
        path: {
          recording_id: recordingId
        }
      },
      body: {
        client_command_id: payload.clientCommandId,
        kind: payload.kind,
        forwarding_ack: forwardingAck,
        payload: normalizeInteractionPayload(payload),
        source: 'scrcpy_bridge'
      }
    })
  )
  return {
    entry: normalizeTimelineEntry(data.entry)
  }
}

export async function getRecordingTimeline(recordingId: string): Promise<RecordingTimelineData> {
  const data = await unwrapData<components['schemas']['SuccessResponse_RecordingTimelineData_']>(
    client.GET('/v1/recordings/{recording_id}/timeline', {
      params: {
        path: {
          recording_id: recordingId
        }
      }
    })
  )
  return {
    timeline: (data.timeline ?? []).map(normalizeTimelineEntry)
  }
}

export async function getRecordingObservation(
  recordingId: string,
  observationId: string
): Promise<RecordingObservationData> {
  return unwrapData<components['schemas']['SuccessResponse_RecordingObservationData_']>(
    client.GET('/v1/recordings/{recording_id}/observations/{observation_id}', {
      params: {
        path: {
          recording_id: recordingId,
          observation_id: observationId
        }
      }
    })
  )
}

export async function stopRecordingSession(recordingId: string): Promise<RecordingSessionData> {
  const data = await unwrapData<components['schemas']['SuccessResponse_RecordingSessionData_']>(
    client.POST('/v1/recordings/{recording_id}/stop', {
      params: {
        path: {
          recording_id: recordingId
        }
      }
    })
  )
  return {
    session: normalizeSession(data.session)
  }
}

export async function cancelRecordingSession(recordingId: string): Promise<RecordingSessionData> {
  const data = await unwrapData<components['schemas']['SuccessResponse_RecordingSessionData_']>(
    client.POST('/v1/recordings/{recording_id}/cancel', {
      params: {
        path: {
          recording_id: recordingId
        }
      }
    })
  )
  return {
    session: normalizeSession(data.session)
  }
}

export async function getRecordingAnalysis(recordingId: string): Promise<RecordingAnalysisData> {
  return unwrapData<components['schemas']['SuccessResponse_RecordingAnalysisData_']>(
    client.GET('/v1/recordings/{recording_id}/analysis', {
      params: {
        path: {
          recording_id: recordingId
        }
      }
    })
  )
}

export async function startRecordingAnalysis(recordingId: string): Promise<RecordingAnalysisSubmissionData> {
  return unwrapData<components['schemas']['SuccessResponse_OperationSubmissionData_']>(
    client.POST('/v1/recordings/{recording_id}/analysis', {
      params: {
        path: {
          recording_id: recordingId
        }
      }
    })
  )
}

export async function exportRecordingCase(recordingId: string): Promise<RecordingExportData> {
  const data = await unwrapData<components['schemas']['SuccessResponse_RecordingExportData_']>(
    client.POST('/v1/recordings/{recording_id}/export-case', {
      params: {
        path: {
          recording_id: recordingId
        }
      }
    })
  )
  return {
    analysis: data.analysis,
    case: data.case,
    artifacts: data.artifacts ?? {}
  }
}

export async function replayRecordingCase(recordingId: string): Promise<RecordingReplayData> {
  return unwrapData<components['schemas']['SuccessResponse_RecordingReplayData_']>(
    client.POST('/v1/recordings/{recording_id}/replay-case', {
      params: {
        path: {
          recording_id: recordingId
        }
      }
    })
  )
}
