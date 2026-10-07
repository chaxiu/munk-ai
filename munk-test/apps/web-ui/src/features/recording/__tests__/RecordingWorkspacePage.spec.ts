import { computed, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { typedViFn } from '@/shared/testing/typedViFn'
import UiSelect from '@/shared/ui/UiSelect.vue'

type RecordingSession = {
  recording_id: string
  app_id: string
  case_id: string | null
  entry_identity: string | null
  device_ref: string | null
  status: 'created' | 'recording' | 'stopped'
  asset_dir: string
  created_at: string
  started_at: string | null
  finished_at: string | null
  latest_frame_seq: number | null
  failure_reason: string | null
}
type RecordingEvent = Record<string, unknown>
type RecordingTimelineItem = Record<string, unknown>
type RecordingAnalysis = {
  recording_id: string
  status: string
  test_case: {
    case_id: string
    title: string
    intent: string
    preconditions: string[]
    expected: string[]
    procedure: string[]
    runner_goal: string
    start_state: {
      mode: string
      page_id: string | null
    }
  }
  steps: Array<{
    entry_id: string
    seq: number
    kind: string
    summary?: string | null
    action?: string | null
    intent?: string | null
    state_change?: string | null
    procedure_step?: string | null
    warnings?: string[]
    action_evidence?: {
      raw_action_summary?: string | null
      before_entry_identity?: string | null
      after_entry_identity?: string | null
      before_surface_identity?: string | null
      after_surface_identity?: string | null
      resolved_target?: {
        label?: string | null
        kind?: string | null
        confidence?: number | null
      } | null
      target_candidates?: Array<{
        rank?: number
        label?: string | null
        kind?: string | null
        confidence?: number | null
      }>
    } | null
    outcome_evidence?: {
      screen_diff_summary?: string | null
      before_entry_identity?: string | null
      after_entry_identity?: string | null
      before_surface_identity?: string | null
      after_surface_identity?: string | null
    } | null
  }>
  source_summary: string
  warnings: string[]
  export_ready: boolean
  failure_reason: string | null
}
type ExportedCase = {
  recording_id: string
  case_id: string
  case_path: string
  analysis_path: string
  plan_id?: string | null
  plan_path?: string | null
  snapshot_path?: string | null
  exported_at: string
}
type ReplayResult = {
  recording_id: string
  case_id: string
  operation_id: string
  run_dir: string
  result_path: string
  artifact_manifest_path: string
  verdict: string
  replayed_at: string
}
type AnalysisOperation = {
  operation_id: string
  status: 'queued' | 'running' | 'succeeded' | 'failed'
  error_message?: string | null
  progress?: Record<string, unknown>
}
type SessionQueryResult = {
  data: {
    session: RecordingSession | null
    events: RecordingEvent[]
    timeline: RecordingTimelineItem[]
  }
}
type TimelineQueryResult = {
  data: {
    timeline: RecordingTimelineItem[]
  }
}
type SessionMutationResult = { session: RecordingSession | null }
type BeginSessionMutationResult = {
  session: RecordingSession | null
  bridge: {
    recording_id: string
    base_url: string
    ws_url: string
  }
}
type AnalysisMutationResult = {
  operation_id: string
  status: string
  app_id?: string | null
  phase?: string | null
}
type ExportMutationResult = {
  analysis: RecordingAnalysis | null
  case: ExportedCase | null
  artifacts: Record<string, unknown>
}
type ReplayMutationResult = { replay: ReplayResult | null }
type RecordInteractionMutationResult = Record<string, never>

const session = ref<RecordingSession | null>(null)
const events = ref<RecordingEvent[]>([])
const timeline = ref<RecordingTimelineItem[]>([])
const analysis = ref<RecordingAnalysis | null>(null)
const analysisOperation = ref<AnalysisOperation | null>(null)
const analysisEvents = ref<Array<{ seq: number, event_type: string, message: string, timestamp: string }>>([])
const analysisError = ref<unknown>(null)
const exportedCase = ref<ExportedCase | null>(null)
const replayResult = ref<ReplayResult | null>(null)
const apps = ref([
  {
    app_id: 'demo-app',
    platform: 'android',
    entry_identity: 'com.example.demo',
    introduction_exists: true,
    plan_count: 0,
    case_count: 0,
  },
])

const state = {
  session,
  events,
  timeline,
  analysis,
  analysisOperation,
  analysisEvents,
  analysisError,
  exportedCase,
  replayResult,
  refetchSession: vi.fn<() => Promise<SessionQueryResult>>(async () => ({
    data: {
      session: session.value,
      events: events.value,
      timeline: timeline.value,
    },
  })),
  refetchTimeline: vi.fn<() => Promise<TimelineQueryResult>>(async () => ({
    data: {
      timeline: timeline.value,
    },
  })),
  createSession: vi.fn<(input: { appId: string, entryIdentity: string, deviceRef?: string }) => Promise<SessionMutationResult>>(async (input) => {
    session.value = {
      recording_id: 'rec-1',
      app_id: input.appId,
      case_id: null,
      entry_identity: input.entryIdentity,
      device_ref: input.deviceRef ?? null,
      status: 'created',
      asset_dir: '/tmp/rec-1',
      created_at: '2026-01-01T00:00:00Z',
      started_at: null,
      finished_at: null,
      latest_frame_seq: null,
      failure_reason: null,
    }
    return { session: session.value }
  }),
  beginSession: vi.fn<() => Promise<BeginSessionMutationResult>>(async () => {
    if (!session.value) {
      throw new Error('expected session before begin')
    }
    session.value = {
      ...session.value,
      status: 'recording',
      latest_frame_seq: 1,
    }
    return {
      session: session.value,
      bridge: {
        recording_id: 'rec-1',
        base_url: 'http://127.0.0.1:17960',
        ws_url: 'ws://127.0.0.1:17960/sessions/rec-1/stream',
      },
    }
  }),
  stopSession: vi.fn<() => Promise<SessionMutationResult>>(async () => {
    if (!session.value) {
      throw new Error('expected session before stop')
    }
    session.value = {
      ...session.value,
      status: 'stopped',
      finished_at: '2026-01-01T00:00:05Z',
    }
    return { session: session.value }
  }),
  analyzeSession: vi.fn<() => Promise<AnalysisMutationResult>>(async () => {
    analysisOperation.value = {
      operation_id: 'op-analysis-1',
      status: 'succeeded',
      error_message: null,
      progress: {
        phase: 'completed',
        completed_steps: 1,
        total_steps: 1,
      },
    }
    analysisEvents.value = [{
      seq: 1,
      event_type: 'recording_analysis_completed',
      message: 'recording analysis completed',
      timestamp: '2026-01-01T00:00:06Z',
    }]
    return {
      operation_id: 'op-analysis-1',
      status: 'queued',
      app_id: 'demo-app',
      phase: 'queued',
    }
  }),
  fetchAnalysis: typedViFn(async () => {
    analysis.value = {
      recording_id: 'rec-1',
      status: 'completed',
      test_case: {
        case_id: 'case-generated',
        title: 'Generated Case',
        intent: 'Verify the recorded flow',
        preconditions: [],
        expected: ['The visible state changes as expected'],
        procedure: ['Tap generated button'],
        runner_goal: 'Replay the recorded flow and verify the visible state change',
        start_state: {
          mode: 'reset',
          page_id: null,
        },
      },
      steps: [
        {
          entry_id: 'entry-1',
          seq: 1,
          kind: 'click',
          summary: 'tap generated button',
          action: '点击 Generated button',
          intent: '打开成功页',
          state_change: '成功提示显示',
          procedure_step: '打开成功页，点击 Generated button，成功提示显示',
          warnings: ['surface identity unavailable'],
          action_evidence: {
            raw_action_summary: 'click at (120, 220) on 1080x2400 screen',
            before_entry_identity: 'com.example.demo',
            after_entry_identity: 'com.example.demo',
            before_surface_identity: 'com.example.demo/.MainActivity',
            after_surface_identity: 'com.example.demo/.DetailActivity',
            resolved_target: {
              label: 'Generated button',
              kind: 'button',
              confidence: 0.96,
            },
            target_candidates: [
              {
                rank: 1,
                label: 'Generated button',
                kind: 'button',
                confidence: 0.96,
              },
            ],
          },
          outcome_evidence: {
            screen_diff_summary: 'screen_changed=yes; appeared_nodes=Success',
            before_entry_identity: 'com.example.demo',
            after_entry_identity: 'com.example.demo',
            before_surface_identity: 'com.example.demo/.MainActivity',
            after_surface_identity: 'com.example.demo/.DetailActivity',
          },
        },
      ],
      source_summary: 'recording rec-1 for app demo-app with 1 timeline steps',
      warnings: [],
      export_ready: true,
      failure_reason: null,
    }
    return { analysis: analysis.value }
  }),
  exportCase: vi.fn<() => Promise<ExportMutationResult>>(async () => {
    exportedCase.value = {
      recording_id: 'rec-1',
      case_id: 'case-generated',
      case_path: '/tmp/rec-1/case/test_case.json',
      analysis_path: '/tmp/rec-1/case/analysis.json',
      plan_id: 'recording_rec-1',
      plan_path: '/tmp/home/assets/plans/demo-app/recording_rec-1.json',
      snapshot_path: '/tmp/home/assets/plans/demo-app/snapshots/recording_rec-1-20260101000010.json',
      exported_at: '2026-01-01T00:00:10Z',
    }
    return {
      analysis: analysis.value,
      case: exportedCase.value,
      artifacts: {},
    }
  }),
  replayCase: vi.fn<() => Promise<ReplayMutationResult>>(async () => {
    replayResult.value = {
      recording_id: 'rec-1',
      case_id: 'case-generated',
      operation_id: 'op-replay-1',
      run_dir: '/tmp/rec-1/runs/op-replay-1',
      result_path: '/tmp/rec-1/runs/op-replay-1/result.json',
      artifact_manifest_path: '/tmp/rec-1/runs/op-replay-1/artifact_manifest.json',
      verdict: 'passed',
      replayed_at: '2026-01-01T00:00:20Z',
    }
    return { replay: replayResult.value }
  }),
  recordInteraction: vi.fn<() => Promise<RecordInteractionMutationResult>>(async () => ({})),
}

const { getRecordingAnalysisMock } = vi.hoisted(() => ({
  getRecordingAnalysisMock: vi.fn(),
}))

vi.mock('../queries/useRecordingSessionQuery', () => ({
  useRecordingSessionQuery: () => ({
    data: computed(() => state.session.value ? {
      session: state.session.value,
      events: state.events.value,
      timeline: state.timeline.value,
    } : undefined),
    isFetching: ref(false),
    refetch: state.refetchSession,
  }),
}))

vi.mock('../queries/useRecordingTimelineQuery', () => ({
  useRecordingTimelineQuery: () => ({
    data: computed(() => state.session.value ? {
      timeline: state.timeline.value,
    } : undefined),
    isFetching: ref(false),
    refetch: state.refetchTimeline,
  }),
}))

vi.mock('../queries/useRecordingMutations', () => ({
  useRecordingMutations: () => ({
    createSession: { isPending: ref(false), mutateAsync: state.createSession },
    beginSession: { isPending: ref(false), mutateAsync: state.beginSession },
    stopSession: { isPending: ref(false), mutateAsync: state.stopSession },
    analyzeSession: { isPending: ref(false), mutateAsync: state.analyzeSession },
    exportCase: { isPending: ref(false), mutateAsync: state.exportCase },
    replayCase: { isPending: ref(false), mutateAsync: state.replayCase },
    recordInteraction: { isPending: ref(false), mutateAsync: state.recordInteraction },
  }),
}))

vi.mock('../queries/useRecordingAnalysisProgress', () => ({
  useRecordingAnalysisProgress: () => ({
    operation: state.analysisOperation,
    events: state.analysisEvents,
    loading: ref(false),
    error: state.analysisError,
    polling: ref(false),
    isFinished: () => ['succeeded', 'failed', 'cancelled'].includes(state.analysisOperation.value?.status ?? ''),
    refetch: typedViFn(),
  }),
}))

vi.mock('@/features/apps/queries/useAppsQuery', () => ({
  useAppsQuery: () => ({
    data: computed(() => apps.value),
    error: ref(null),
    isFetching: ref(false),
  }),
}))

vi.mock('@/features/devices/queries/useDevicesQuery', () => ({
  useDevicesQuery: () => ({
    data: computed(() => [{
      platform: 'android',
      device_ref: 'emulator-5554',
      display_name: 'Pixel 8 Pro',
      kind: 'emulator',
      availability: 'available',
      is_booted: true,
      raw: {},
    }]),
    error: ref(null),
    isFetching: ref(false),
    refetch: typedViFn(),
  }),
}))

vi.mock('../components/ScrcpySurface.vue', () => ({
  default: {
    template: '<div class="scrcpy-surface-stub">surface</div>',
  },
}))

vi.mock('@/shared/api/recording', async () => {
  const actual = await vi.importActual<typeof import('@/shared/api/recording')>('@/shared/api/recording')
  return {
    ...actual,
    getRecordingAnalysis: getRecordingAnalysisMock,
  }
})

import RecordingWorkspacePage from '../pages/RecordingWorkspacePage.vue'
import { setLocale, i18n } from '@/shared/i18n'

vi.mock('vue-router', async () => {
  const actual = await vi.importActual<typeof import('vue-router')>('vue-router')
  return {
    ...actual,
  }
})

describe('RecordingWorkspacePage', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-01-01T00:10:30Z'))
    setLocale('en-US')
    state.session.value = null
    state.events.value = []
    state.timeline.value = []
    state.analysis.value = null
    state.analysisOperation.value = null
    state.analysisEvents.value = []
    state.analysisError.value = null
    state.exportedCase.value = null
    state.replayResult.value = null
    apps.value = [
      {
        app_id: 'demo-app',
        platform: 'android',
        entry_identity: 'com.example.demo',
        introduction_exists: true,
        plan_count: 0,
        case_count: 0,
      },
    ]
    state.refetchSession.mockClear()
    state.refetchTimeline.mockClear()
    state.createSession.mockClear()
    getRecordingAnalysisMock.mockReset()
    getRecordingAnalysisMock.mockImplementation(state.fetchAnalysis)
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  function findButtonByText(wrapper: ReturnType<typeof mount>, label: string) {
    return wrapper.findAll('button').find((button) => button.text() === label)
  }

  it('renders analysis, export metadata, and replay result after a stopped recording', async () => {
    const wrapper = mount(RecordingWorkspacePage, {
      global: {
        plugins: [i18n],
        stubs: {
          RouterLink: {
            props: ['to'],
            template: '<a :href="typeof to === \'string\' ? to : \'\'"><slot /></a>',
          },
        },
      },
    })

    const selects = wrapper.findAllComponents(UiSelect)
    selects[0]?.vm.$emit('update:modelValue', 'emulator-5554')
    selects[1]?.vm.$emit('update:modelValue', 'demo-app')
    await flushPromises()

    await findButtonByText(wrapper, 'Create session')?.trigger('click')
    await flushPromises()
    await findButtonByText(wrapper, 'Begin')?.trigger('click')
    await flushPromises()
    await findButtonByText(wrapper, 'Stop')?.trigger('click')
    await flushPromises()
    await findButtonByText(wrapper, 'Analyze')?.trigger('click')
    await flushPromises()
    await findButtonByText(wrapper, 'Export case')?.trigger('click')
    await flushPromises()
    await findButtonByText(wrapper, 'Replay case')?.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Select Android device')
    expect(wrapper.text()).not.toContain('Session Controls')
    expect(wrapper.text()).not.toContain('Configure the target app, select a device and drive the recording / analysis loop.')
    expect(wrapper.text()).toContain('Generated Case')
    expect(wrapper.text()).toContain('Verify the recorded flow')
    expect(wrapper.text()).toContain('Analysis Evidence')
    expect(wrapper.text()).toContain('Generated button')
    expect(wrapper.text()).toContain('surface identity unavailable')
    expect(wrapper.text()).toContain('/tmp/rec-1/case/test_case.json')
    expect(wrapper.text()).toContain('recording_rec-1')
    expect(wrapper.text()).toContain('/tmp/home/assets/plans/demo-app/recording_rec-1.json')
    expect(wrapper.text()).toContain('op-replay-1')
    expect(wrapper.text()).toContain('/tmp/rec-1/runs/op-replay-1')
    expect(wrapper.text()).toContain('Open Run Detail')
    expect(wrapper.text()).toContain('Open Tests Plan')
    expect(wrapper.findAll('time').length).toBeGreaterThan(0)
    expect(wrapper.text()).not.toContain('2026-01-01T00:00:05Z')
    expect(state.createSession).toHaveBeenCalledWith({
      appId: 'demo-app',
      entryIdentity: 'com.example.demo',
      deviceRef: 'emulator-5554',
    })
  })
})
