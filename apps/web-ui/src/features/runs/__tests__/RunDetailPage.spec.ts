import { computed, ref } from 'vue'
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { typedViFn } from '@/shared/testing/typedViFn'

import RunDetailPage from '../pages/RunDetailPage.vue'
import { i18n, setLocale } from '@/shared/i18n'

const { getArtifactContentMock, cancelMock, reproduceMock, useRunEventsQueryMock } = vi.hoisted(() => ({
  getArtifactContentMock: vi.fn(async () => ({
    artifact_id: 'result',
    media_type: 'application/json',
    encoding: 'utf-8',
    truncated: false,
    content: '{"status":"ok"}',
  })),
  cancelMock: vi.fn(async () => ({ operation_id: 'op-1', status: 'running', cancel_requested: true })),
  reproduceMock: vi.fn(async () => ({ operation_id: 'op-1', status: 'succeeded', reproduction_entries: [{ id: 'r1' }] })),
  useRunEventsQueryMock: vi.fn(),
}))

function buildDetailState() {
  return {
    operation_id: 'op-1',
    kind: 'run_case',
    run_type: 'case_run',
    title: 'Open settings',
    platform: 'android',
    phase: null,
    target_label: 'demo-app / plan-1 / case-1',
    source_recording_id: null,
    status: 'failed',
    verification_verdict: 'failed',
    app_id: 'demo-app',
    plan_id: 'plan-1',
    case_id: 'case-1',
    pid: null,
    cancel_requested: false,
    device_ref: 'emulator-5554',
    resource_scope: null,
    conflict_reason: null,
    created_at: '2026-01-01T00:00:00Z',
    started_at: '2026-01-01T00:00:01Z',
    finished_at: '2026-01-01T00:00:05Z',
    error_code: null,
    error_message: null,
    progress: { stage: 'done' },
    result: {
      plan_id: 'plan-1',
      case_id: 'case-1',
      verdict: 'failed',
      attempt_count: 2,
      attempts: [
        {
          attempt_index: 0,
          verdict: 'inconclusive',
          summary: 'The first attempt ended without enough evidence.',
          judge_reason: 'The expected screen was not stable enough to conclude.',
          retry_reason: 'The judge asked for one more runner pass with extra context.',
          supplemental_context: ['Re-check the final settings header before stopping.'],
          missing_evidence: ['stable final screenshot'],
          confidence: 0.42,
          execution: {
            status: 'completed',
            stop_reason: 'agent_stop',
            steps_completed: 4,
            error_message: null,
            error_type: null,
            last_action_summary: 'Reached settings entry',
            last_target_identity: 'com.example.demo',
            last_surface_identity: 'com.example.demo/.SettingsActivity',
          },
          runner_run_dir: '/tmp/run-1-attempt-1',
        },
        {
          attempt_index: 1,
          verdict: 'failed',
          summary: 'Settings page is visible.',
          judge_reason: 'The expected settings screen is present.',
          retry_reason: 'The judge asked for one more runner pass with extra context.',
          supplemental_context: ['Re-check the final settings header before stopping.'],
          missing_evidence: [],
          confidence: 0.91,
          execution: {
            status: 'completed',
            stop_reason: 'agent_stop',
            steps_completed: 5,
            error_message: null,
            error_type: null,
            last_action_summary: 'Opened settings',
            last_target_identity: 'com.example.demo',
            last_surface_identity: 'com.example.demo/.SettingsActivity',
          },
          runner_run_dir: '/tmp/run-1-attempt-2',
        },
      ],
      final_decision: {
        decision_type: 'finish',
        reason: 'The second attempt produced a stable result.',
        summary: 'The workflow stopped after the second judged attempt.',
      },
      execution: {
        status: 'completed',
        stop_reason: 'agent_stop',
        steps_completed: 5,
        error_message: null,
        error_type: null,
        last_action_summary: 'Opened settings',
        last_target_identity: 'com.example.demo',
        last_surface_identity: 'com.example.demo/.SettingsActivity',
      },
      run_dir: '/tmp/run-1',
      artifacts: { result: '/tmp/run-1/result.json' },
      summary: 'Settings page is visible.',
      judge_reason: 'The expected settings screen is present.',
      failure_hypothesis: null,
      confidence: 0.91,
      missing_evidence: [],
      supporting_evidence_ids: ['screen-final'],
      supplemental_context: ['Re-check the final settings header before stopping.'],
      evidence: [
        {
          evidence_id: 'screen-final',
          kind: 'screen_frame',
          source: 'artifact',
          summary: 'Final screen shows Settings title',
          payload: {
            path: '/tmp/run-1/result.json',
            step_index: 5,
            excerpt: { title: 'Settings' },
          },
        },
        {
          evidence_id: 'event-32',
          kind: 'event',
          source: 'event',
          summary: 'action proposed for step 3 | data={"action":"stop","summary":"The new task Test is visible in the task list, satisfying the objective.","step":3}',
          payload: {
            excerpt: {
              action: 'stop',
              summary: 'The new task Test is visible in the task list, satisfying the objective.',
              step: 3,
            },
          },
        },
        {
          evidence_id: 'runner-history',
          kind: 'runner_history',
          source: 'artifact',
          summary: 'runner_history artifact: latest=stop; outcome=The new task Test is visible in the task list, satisfying the objective.',
          payload: {
            path: '/tmp/run-1/runner_history.json',
          },
        },
        {
          evidence_id: 'trace-7',
          kind: 'decision_trace',
          source: 'artifact',
          summary: '[SCREEN] target_identity=com.boycoder.todo surface_identity=com.boycoder.todo/.MainActivity screen_size=1440x2960 elements=25 tree=nodes=31',
          payload: {
            step_index: 4,
          },
        },
        {
          evidence_id: 'execution-1',
          kind: 'execution',
          source: 'execution',
          summary: 'execution outcome status=completed; stop_reason=agent_stop; steps_completed=4; last_action_summary=The new task Test is visible in the task list.',
          payload: {
            step_index: 4,
          },
        },
        {
          evidence_id: 'event-99',
          kind: 'event',
          source: 'event',
          summary: 'Perception completed',
          payload: {
            step_index: 2,
          },
        },
      ],
    },
    artifact_manifest_path: '/tmp/manifest.json',
    repro_dir: '/tmp/repro',
    primary_artifact_ids: ['result'],
    artifact_manifest_version: 1,
    schema_versions: { review_result: 'v1' },
    diagnostics_path: '/tmp/diagnostics.json',
    duration_ms: 4000,
    failure_category: null,
    warning_summary: [],
  }
}

const detailState = ref<Record<string, unknown>>(buildDetailState() as Record<string, unknown>)

const artifactsState = ref({
  operation_id: 'op-1',
  run_type: 'case_run',
  title: 'Open settings',
  platform: 'android',
  phase: null,
  target_label: 'demo-app / plan-1 / case-1',
  source_recording_id: null,
  status: 'failed',
  verification_verdict: 'failed',
  device_ref: 'emulator-5554',
  resource_scope: null,
  conflict_reason: null,
  artifact_manifest_path: '/tmp/manifest.json',
  repro_dir: '/tmp/repro',
  primary_artifact_ids: ['result'],
  artifact_manifest_version: 1,
  schema_versions: { review_result: 'v1' },
  diagnostics_path: '/tmp/diagnostics.json',
  duration_ms: 4000,
  failure_category: null,
  warning_summary: [],
  case_runs: [
    {
      case_id: 'case-1',
      operation_id: 'op-1',
      title: 'Open settings',
      verdict: 'failed',
      execution_status: 'completed',
      run_dir: '/tmp/run-1',
    },
  ],
  reproduction_entries: [],
  upstream_review: null,
  primary_artifacts: [
    {
      artifact_id: 'result',
      role: 'result',
      kind: 'report',
      scope: 'run',
      media_type: 'application/json',
      exists: true,
      label: 'result',
      case_id: null,
      path: '/tmp/run-1/result.json',
      metadata: {},
      content_url: '/v1/runs/op-1/artifacts/result/content',
      download_url: '/v1/runs/op-1/artifacts/result/download',
    },
    {
      artifact_id: 'raw_screenshots',
      role: 'raw_screenshots',
      kind: 'image_directory',
      scope: 'case_run',
      media_type: null,
      exists: true,
      label: 'raw_screenshots',
      case_id: null,
      path: '/tmp/run-1/screenshots/raw',
      metadata: {},
      content_url: null,
      download_url: null,
    },
  ],
  artifact_groups: [
    {
      group_id: 'primary',
      title: 'Primary Artifacts',
      items: [
        {
          artifact_id: 'result',
          role: 'result',
          kind: 'report',
          scope: 'run',
          media_type: 'application/json',
          exists: true,
          label: 'result',
          case_id: null,
          path: '/tmp/run-1/result.json',
          metadata: {},
          content_url: '/v1/runs/op-1/artifacts/result/content',
          download_url: '/v1/runs/op-1/artifacts/result/download',
        },
        {
          artifact_id: 'raw_screenshots',
          role: 'raw_screenshots',
          kind: 'image_directory',
          scope: 'case_run',
          media_type: null,
          exists: true,
          label: 'raw_screenshots',
          case_id: null,
          path: '/tmp/run-1/screenshots/raw',
          metadata: {},
          content_url: null,
          download_url: null,
        },
      ],
    },
  ],
})

const eventsState = ref({
  operation_id: 'op-1',
  after_seq: 0,
  limit: 200,
  next_after_seq: 5,
  items: [
    {
      seq: 1,
      operation_id: 'op-1',
      event_type: 'workflow_started',
      message: 'workflow started',
      timestamp: '2026-01-01T00:00:01Z',
      agent_role: 'orchestration',
      timeline_scope: 'parent_run',
      timeline_phase: 'started',
      summary: 'Workflow started for this case run.',
      data_json: {
        agent_role: 'orchestration',
        timeline_scope: 'parent_run',
        timeline_phase: 'started',
        summary: 'Workflow started for this case run.',
      },
    },
    {
      seq: 2,
      operation_id: 'op-1',
      event_type: 'context_prepare_completed',
      message: 'context prepared',
      timestamp: '2026-01-01T00:00:02Z',
      agent_role: 'context_prepare',
      timeline_scope: 'parent_run',
      timeline_phase: 'completed',
      attempt_index: 0,
      summary: 'Loaded device state and prepared runtime context.',
      data_json: {
        agent_role: 'context_prepare',
        timeline_scope: 'parent_run',
        timeline_phase: 'completed',
        attempt_index: 0,
        summary: 'Loaded device state and prepared runtime context.',
      },
    },
    {
      seq: 3,
      operation_id: 'op-1',
      event_type: 'runner_completed',
      message: 'runner completed attempt 1',
      timestamp: '2026-01-01T00:00:03Z',
      agent_role: 'runner',
      timeline_scope: 'parent_run',
      timeline_phase: 'completed',
      attempt_index: 0,
      summary: 'Runner completed the first attempt.',
      data_json: {
        agent_role: 'runner',
        timeline_scope: 'parent_run',
        timeline_phase: 'completed',
        attempt_index: 0,
        summary: 'Runner completed the first attempt.',
        step_count: 5,
      },
    },
    {
      seq: 4,
      operation_id: 'op-1',
      event_type: 'judge_decision_ready',
      message: 'judge completed review',
      timestamp: '2026-01-01T00:00:04Z',
      agent_role: 'judge',
      timeline_scope: 'parent_run',
      timeline_phase: 'decision_ready',
      attempt_index: 0,
      summary: 'Judge concluded the case should finish.',
      data_json: {
        agent_role: 'judge',
        timeline_scope: 'parent_run',
        timeline_phase: 'decision_ready',
        attempt_index: 0,
        summary: 'Judge concluded the case should finish.',
        verdict: 'failed',
      },
    },
    {
      seq: 5,
      operation_id: 'op-1',
      event_type: 'child_operation_submitted',
      message: 'submitted optimize operation',
      timestamp: '2026-01-01T00:00:05Z',
      agent_role: 'optimize',
      timeline_scope: 'parent_run',
      timeline_phase: 'submitted',
      child_operation_id: 'op-optimize-1',
      summary: 'Submitted optimize follow-up operation.',
      data_json: {
        agent_role: 'optimize',
        timeline_scope: 'parent_run',
        timeline_phase: 'submitted',
        child_operation_id: 'op-optimize-1',
        summary: 'Submitted optimize follow-up operation.',
      },
    },
  ],
})

const childrenState = ref({
  operation_id: 'op-1',
  artifact_id: 'raw_screenshots',
  title: 'raw_screenshots',
  kind: 'image_directory',
  items: [
    {
      child_id: 'step_0001.png',
      name: 'step_0001.png',
      path: '/tmp/run-1/screenshots/raw/step_0001.png',
      media_type: 'image/png',
      size_bytes: 120,
      content_url: '/v1/runs/op-1/artifacts/raw_screenshots/children/step_0001.png/content',
    },
    {
      child_id: 'step_0002.png',
      name: 'step_0002.png',
      path: '/tmp/run-1/screenshots/raw/step_0002.png',
      media_type: 'image/png',
      size_bytes: 121,
      content_url: '/v1/runs/op-1/artifacts/raw_screenshots/children/step_0002.png/content',
    },
  ],
})

const refetchMock = typedViFn(async () => ({ data: null }))
const routerPushMock = vi.fn()
const devicesState = ref([
  {
    device_ref: 'emulator-5554',
    display_name: 'Pixel 8',
    platform: 'android',
  },
])

const knowledgeCandidatesState = ref({
  items: [
    {
      candidate_id: 'candidate-1',
      app_id: 'demo-app',
      status: 'pending_review',
      submitted_at: '2026-01-01T00:00:00Z',
      candidate: {
        app_id: 'demo-app',
        title: 'Login issue',
        card_type: 'issue',
        confidence: 0.82,
        source: { kind: 'knowledge_agent', note: 'test' },
        payload: {
          symptom: 'login failed',
          trigger: 'tap login',
          workaround: 'retry',
        },
      },
      evidence_refs: [],
    },
  ],
})

vi.mock('vue-router', async () => {
  const actual = await vi.importActual<typeof import('vue-router')>('vue-router')
  return {
    ...actual,
    useRoute: () => ({
      params: {
        operationId: 'op-1',
      },
    }),
    useRouter: () => ({
      push: routerPushMock,
    }),
  }
})

vi.mock('../queries/useRunDetailQuery', () => ({
  useRunDetailQuery: () => ({
    data: computed(() => detailState.value),
    isFetching: ref(false),
    error: ref(null),
    refetch: refetchMock,
  }),
}))

vi.mock('../queries/useRunArtifactsQuery', () => ({
  useRunArtifactsQuery: () => ({
    data: computed(() => artifactsState.value),
    isFetching: ref(false),
    error: ref(null),
    refetch: refetchMock,
  }),
}))

vi.mock('../queries/useRunEventsQuery', () => ({
  useRunEventsQuery: (...args: unknown[]) => useRunEventsQueryMock(...args),
}))

vi.mock('../queries/useRunArtifactChildrenQuery', () => ({
  useRunArtifactChildrenQuery: () => ({
    data: computed(() => childrenState.value),
    isFetching: ref(false),
    error: ref(null),
    refetch: refetchMock,
  }),
}))

vi.mock('@/features/devices/queries/useDevicesQuery', () => ({
  useDevicesQuery: () => ({
    data: computed(() => devicesState.value),
    isFetching: ref(false),
    error: ref(null),
  }),
}))

vi.mock('@/features/apps/queries/useAppKnowledgeCandidatesQuery', () => ({
  useAppKnowledgeCandidatesQuery: () => ({
    data: computed(() => knowledgeCandidatesState.value),
    isFetching: ref(false),
    error: ref(null),
  }),
}))

vi.mock('@/shared/api/operations', async () => {
  const actual = await vi.importActual<typeof import('@/shared/api/operations')>('@/shared/api/operations')
  return {
    ...actual,
    getOperationArtifactContent: getArtifactContentMock,
    cancelOperation: cancelMock,
    reproduceOperation: reproduceMock,
  }
})

enableAutoUnmount(afterEach)

describe('RunDetailPage', () => {
  beforeEach(() => {
    setLocale('en-US')
    getArtifactContentMock.mockClear()
    cancelMock.mockClear()
    reproduceMock.mockClear()
    useRunEventsQueryMock.mockReset()
    routerPushMock.mockClear()
    useRunEventsQueryMock.mockImplementation(() => ({
      data: computed(() => eventsState.value),
      isFetching: ref(false),
      error: ref(null),
      refetch: refetchMock,
    }))
    detailState.value = buildDetailState()
    eventsState.value = {
      operation_id: 'op-1',
      after_seq: 0,
      limit: 200,
      next_after_seq: 5,
      items: [
        {
          seq: 1,
          operation_id: 'op-1',
          event_type: 'workflow_started',
          message: 'workflow started',
          timestamp: '2026-01-01T00:00:01Z',
          agent_role: 'orchestration',
          timeline_scope: 'parent_run',
          timeline_phase: 'started',
          summary: 'Workflow started for this case run.',
          data_json: {
            agent_role: 'orchestration',
            timeline_scope: 'parent_run',
            timeline_phase: 'started',
            summary: 'Workflow started for this case run.',
          },
        },
        {
          seq: 2,
          operation_id: 'op-1',
          event_type: 'context_prepare_completed',
          message: 'context prepared',
          timestamp: '2026-01-01T00:00:02Z',
          agent_role: 'context_prepare',
          timeline_scope: 'parent_run',
          timeline_phase: 'completed',
          attempt_index: 0,
          summary: 'Loaded device state and prepared runtime context.',
          data_json: {
            agent_role: 'context_prepare',
            timeline_scope: 'parent_run',
            timeline_phase: 'completed',
            attempt_index: 0,
            summary: 'Loaded device state and prepared runtime context.',
          },
        },
        {
          seq: 3,
          operation_id: 'op-1',
          event_type: 'runner_completed',
          message: 'runner completed attempt 1',
          timestamp: '2026-01-01T00:00:03Z',
          agent_role: 'runner',
          timeline_scope: 'parent_run',
          timeline_phase: 'completed',
          attempt_index: 0,
          summary: 'Runner completed the first attempt.',
          data_json: {
            agent_role: 'runner',
            timeline_scope: 'parent_run',
            timeline_phase: 'completed',
            attempt_index: 0,
            summary: 'Runner completed the first attempt.',
            step_count: 5,
          },
        },
        {
          seq: 4,
          operation_id: 'op-1',
          event_type: 'judge_decision_ready',
          message: 'judge completed review',
          timestamp: '2026-01-01T00:00:04Z',
          agent_role: 'judge',
          timeline_scope: 'parent_run',
          timeline_phase: 'decision_ready',
          attempt_index: 0,
          summary: 'Judge concluded the case should finish.',
          data_json: {
            agent_role: 'judge',
            timeline_scope: 'parent_run',
            timeline_phase: 'decision_ready',
            attempt_index: 0,
            summary: 'Judge concluded the case should finish.',
            verdict: 'failed',
          },
        },
        {
          seq: 5,
          operation_id: 'op-1',
          event_type: 'child_operation_submitted',
          message: 'submitted optimize operation',
          timestamp: '2026-01-01T00:00:05Z',
          agent_role: 'optimize',
          timeline_scope: 'parent_run',
          timeline_phase: 'submitted',
          child_operation_id: 'op-optimize-1',
          summary: 'Submitted optimize follow-up operation.',
          data_json: {
            agent_role: 'optimize',
            timeline_scope: 'parent_run',
            timeline_phase: 'submitted',
            child_operation_id: 'op-optimize-1',
            summary: 'Submitted optimize follow-up operation.',
          },
        },
      ],
    }
    artifactsState.value = {
      operation_id: 'op-1',
      run_type: 'case_run',
      title: 'Open settings',
      platform: 'android',
      phase: null,
      target_label: 'demo-app / plan-1 / case-1',
      source_recording_id: null,
      status: 'failed',
      verification_verdict: 'failed',
      device_ref: 'emulator-5554',
      resource_scope: null,
      conflict_reason: null,
      artifact_manifest_path: '/tmp/manifest.json',
      repro_dir: '/tmp/repro',
      primary_artifact_ids: ['result'],
      artifact_manifest_version: 1,
      schema_versions: { review_result: 'v1' },
      diagnostics_path: '/tmp/diagnostics.json',
      duration_ms: 4000,
      failure_category: null,
      warning_summary: [],
      case_runs: [
        {
          case_id: 'case-1',
          operation_id: 'op-1',
          title: 'Open settings',
          verdict: 'failed',
          execution_status: 'completed',
          run_dir: '/tmp/run-1',
        },
      ],
      reproduction_entries: [],
      upstream_review: null,
      primary_artifacts: [
        {
          artifact_id: 'result',
          role: 'result',
          kind: 'report',
          scope: 'run',
          media_type: 'application/json',
          exists: true,
          label: 'result',
          case_id: null,
          path: '/tmp/run-1/result.json',
          metadata: {},
          content_url: '/v1/runs/op-1/artifacts/result/content',
          download_url: '/v1/runs/op-1/artifacts/result/download',
        },
        {
          artifact_id: 'raw_screenshots',
          role: 'raw_screenshots',
          kind: 'image_directory',
          scope: 'case_run',
          media_type: null,
          exists: true,
          label: 'raw_screenshots',
          case_id: null,
          path: '/tmp/run-1/screenshots/raw',
          metadata: {},
          content_url: null,
          download_url: null,
        },
      ],
      artifact_groups: [
        {
          group_id: 'primary',
          title: 'Primary Artifacts',
          items: [
            {
              artifact_id: 'result',
              role: 'result',
              kind: 'report',
              scope: 'run',
              media_type: 'application/json',
              exists: true,
              label: 'result',
              case_id: null,
              path: '/tmp/run-1/result.json',
              metadata: {},
              content_url: '/v1/runs/op-1/artifacts/result/content',
              download_url: '/v1/runs/op-1/artifacts/result/download',
            },
            {
              artifact_id: 'raw_screenshots',
              role: 'raw_screenshots',
              kind: 'image_directory',
              scope: 'case_run',
              media_type: null,
              exists: true,
              label: 'raw_screenshots',
              case_id: null,
              path: '/tmp/run-1/screenshots/raw',
              metadata: {},
              content_url: null,
              download_url: null,
            },
          ],
        },
      ],
    }
  })

  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('navigates to case detail from the header action for case runs', async () => {
    const wrapper = mount(RunDetailPage, {
      global: {
        plugins: [i18n],
      },
    })

    await flushPromises()

    const viewCaseButton = wrapper.findAll('button').find((button) => button.text() === 'View Case')
    expect(viewCaseButton).toBeTruthy()
    await viewCaseButton?.trigger('click')

    expect(routerPushMock).toHaveBeenCalledWith({
      name: 'tests-case-detail',
      params: {
        appId: 'demo-app',
        planId: 'plan-1',
        caseId: 'case-1',
      },
    })
    expect(useRunEventsQueryMock).toHaveBeenCalledTimes(1)
    expect(useRunEventsQueryMock.mock.calls[0]).toHaveLength(1)
  })

  it('does not show the case detail action for optimize runs', async () => {
    detailState.value = {
      ...buildDetailState(),
      kind: 'optimize_case',
      run_type: 'optimize_case',
    }

    const wrapper = mount(RunDetailPage, {
      global: {
        plugins: [i18n],
      },
    })

    await flushPromises()

    expect(wrapper.findAll('button').some((button) => button.text() === 'View Case')).toBe(false)
  })

  it('renders summary and raw payload', async () => {
    const wrapper = mount(RunDetailPage, {
      global: {
        plugins: [i18n],
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Open settings')
    expect(wrapper.text()).not.toContain('demo-app / plan-1 / case-1')
    expect(wrapper.text()).toContain('Settings page is visible.')
    expect(wrapper.text()).toContain('The expected settings screen is present.')
    expect(wrapper.text()).toContain('Conclusion')
    expect(wrapper.text()).toContain('Open Primary Evidence')
    expect(wrapper.text()).toContain('Orchestration')
    expect(wrapper.text()).toContain('This run needed 2 attempts before finishing.')
    expect(wrapper.text()).toContain('Finish')
    expect(wrapper.text()).toContain('The second attempt produced a stable result.')
    expect(wrapper.text()).toContain('Re-check the final settings header before stopping.')
    await wrapper.findAll('button').find((button) => button.text() === 'Raw')?.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('"operation_id": "op-1"')
    expect(wrapper.text()).toContain('"summary": "Settings page is visible."')
    expect(wrapper.text()).toContain('"attempt_count": 2')
  })

  it('opens primary evidence from summary actions', async () => {
    const wrapper = mount(RunDetailPage, {
      global: {
        plugins: [i18n],
      },
    })

    await flushPromises()

    await wrapper.findAll('button').find((button) => button.text() === 'Open Primary Evidence')?.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Final screen shows Settings title')
    expect(getArtifactContentMock).toHaveBeenCalledWith('op-1', 'result', { maxBytes: 65536 })
  })

  it('renders timeline and evidence preview', async () => {
    const wrapper = mount(RunDetailPage, {
      global: {
        plugins: [i18n],
      },
    })

    await flushPromises()

    await wrapper.findAll('button').find((button) => button.text() === 'Timeline')?.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Orchestration · Started')
    expect(wrapper.text()).toContain('Context Prepare · Completed')
    expect(wrapper.text()).toContain('Runner · Completed')
    expect(wrapper.text()).toContain('Judge · Decision Ready')
    expect(wrapper.text()).toContain('Optimize · Submitted')
    expect(wrapper.text()).toContain('Child operation: op-optimize-1')
    expect(wrapper.text()).toContain('Debug')
    expect(wrapper.text()).toContain('Event type')
    expect(wrapper.text()).toContain('Workflow started for this case run.')
    expect(wrapper.text()).not.toContain('runner completed attempt 1')

    await wrapper.findAll('button').find((button) => button.text() === 'Evidence')?.trigger('click')
    await flushPromises()
    const evidenceButtons = wrapper.findAll('.evidence-item')
    expect(evidenceButtons[0]?.text()).toContain('Observed screen')
    expect(evidenceButtons[1]?.text()).toContain('Decision trace')
    expect(evidenceButtons[2]?.text()).toContain('Execution summary')
    expect(wrapper.text()).toContain('Observed screen')
    expect(wrapper.text()).toContain('Final screen shows Settings title')
    expect(wrapper.text()).toContain('Proposed action for step 3')
    expect(wrapper.text()).toContain('The new task Test is visible in the task list, satisfying the objective.')
    expect(wrapper.text()).toContain('Runner history')
    expect(wrapper.text()).toContain('Decision trace')
    expect(wrapper.text()).toContain('Observed surface: com.boycoder.todo/.MainActivity')
    expect(wrapper.text()).toContain('Execution summary')
    expect(wrapper.text()).toContain('Perception')
    expect(wrapper.text()).toContain('Perception completed')
    expect(wrapper.text()).not.toContain('action proposed for step 3 | data=')
    expect(getArtifactContentMock).toHaveBeenCalledWith('op-1', 'result', { maxBytes: 65536 })
    expect(wrapper.text()).toContain('{"status":"ok"}')
  })

  it('renders manifest-aware artifacts and disables directory preview', async () => {
    const wrapper = mount(RunDetailPage, {
      global: {
        plugins: [i18n],
      },
    })

    await flushPromises()

    await wrapper.findAll('button').find((button) => button.text() === 'Artifacts')?.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('/tmp/manifest.json')
    expect(wrapper.text()).toContain('/tmp/run-1/result.json')
    expect(wrapper.text()).toContain('Case Runs')
    expect(wrapper.text()).toContain('/tmp/run-1')
    expect(wrapper.text()).toContain('/tmp/run-1/screenshots/raw')
    const screenshotRow = wrapper.text().split('raw_screenshots').join('raw_screenshots')
    expect(screenshotRow).toContain('raw_screenshots')
    expect(wrapper.text()).toContain('View Screenshots')
    expect(wrapper.findAll('a').some((link) => link.text() === 'Download')).toBe(true)
  })

  it('opens non-screenshot artifact preview in a modal', async () => {
    const wrapper = mount(RunDetailPage, {
      global: {
        plugins: [i18n],
      },
    })

    await flushPromises()

    await wrapper.findAll('button').find((button) => button.text() === 'Artifacts')?.trigger('click')
    await flushPromises()
    await wrapper.findAll('button').find((button) => button.text() === 'Preview')?.trigger('click')
    await flushPromises()

    const modal = document.body.querySelector('[data-testid="artifact-preview-modal"]')
    expect(modal).not.toBeNull()
    expect(modal?.textContent).toContain('Artifact Preview')
    expect(modal?.textContent).not.toContain('/tmp/run-1/result.json')

    document.body.querySelector<HTMLButtonElement>('[data-testid="artifact-preview-info-toggle"]')?.click()
    await flushPromises()

    expect(modal?.textContent).toContain('/tmp/run-1/result.json')
    expect(getArtifactContentMock).toHaveBeenCalledWith('op-1', 'result', { maxBytes: 65536 })
    expect(document.body.textContent).toContain('{"status":"ok"}')
  })

  it('opens screenshot browser in a modal', async () => {
    const wrapper = mount(RunDetailPage, {
      global: {
        plugins: [i18n],
      },
    })

    await flushPromises()

    await wrapper.findAll('button').find((button) => button.text() === 'Artifacts')?.trigger('click')
    await flushPromises()
    await wrapper.findAll('button').find((button) => button.text() === 'View Screenshots')?.trigger('click')
    await flushPromises()

    const modal = document.body.querySelector('[data-testid="screenshot-modal"]')
    const previewImage = document.body.querySelector<HTMLImageElement>('img')

    expect(modal).not.toBeNull()
    expect(modal?.textContent).toContain('Screenshot Preview')
    expect(modal?.textContent).toContain('step_0001.png')
    expect(modal?.textContent).not.toContain('/tmp/run-1/screenshots/raw/step_0001.png')
    expect(previewImage?.getAttribute('src')).toBe('/v1/runs/op-1/artifacts/raw_screenshots/children/step_0001.png/content')

    document.body.querySelector<HTMLButtonElement>('[data-testid="screenshot-info-toggle"]')?.click()
    await flushPromises()

    expect(modal?.textContent).toContain('/tmp/run-1/screenshots/raw/step_0001.png')
    expect(modal?.textContent).toContain('/tmp/run-1/screenshots/raw')

    Array.from(document.body.querySelectorAll('button'))
      .find((button) => button.textContent?.includes('step_0002.png'))
      ?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await flushPromises()

    expect(document.body.querySelector('img')?.getAttribute('src')).toBe('/v1/runs/op-1/artifacts/raw_screenshots/children/step_0002.png/content')
  })

  it('closes screenshot modal from the close button and backdrop', async () => {
    const wrapper = mount(RunDetailPage, {
      global: {
        plugins: [i18n],
      },
    })

    await flushPromises()
    await wrapper.findAll('button').find((button) => button.text() === 'Artifacts')?.trigger('click')
    await flushPromises()
    await wrapper.findAll('button').find((button) => button.text() === 'View Screenshots')?.trigger('click')
    await flushPromises()

    const closeButton = document.body.querySelector<HTMLButtonElement>('[data-testid="screenshot-modal-close"]')
    expect(closeButton).not.toBeNull()
    closeButton?.click()
    await flushPromises()

    expect(document.body.querySelector('[data-testid="screenshot-modal"]')).toBeNull()

    await wrapper.findAll('button').find((button) => button.text() === 'View Screenshots')?.trigger('click')
    await flushPromises()

    const backdrop = document.body.querySelector<HTMLButtonElement>('[data-testid="screenshot-modal-backdrop"]')
    expect(backdrop).not.toBeNull()
    backdrop?.click()
    await flushPromises()

    expect(document.body.querySelector('[data-testid="screenshot-modal"]')).toBeNull()
  })

  it('closes screenshot modal when pressing Escape', async () => {
    const wrapper = mount(RunDetailPage, {
      global: {
        plugins: [i18n],
      },
    })

    await flushPromises()
    await wrapper.findAll('button').find((button) => button.text() === 'Artifacts')?.trigger('click')
    await flushPromises()
    await wrapper.findAll('button').find((button) => button.text() === 'View Screenshots')?.trigger('click')
    await flushPromises()

    expect(document.body.querySelector('[data-testid="screenshot-modal"]')).not.toBeNull()

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await flushPromises()

    expect(document.body.querySelector('[data-testid="screenshot-modal"]')).toBeNull()
  })

  it('renders parent run_plan as progress-first view without leaf tabs', async () => {
    detailState.value = {
      ...detailState.value,
      kind: 'run_plan',
      run_type: 'plan_run',
      case_id: null,
      title: 'Run 2 cases in plan-1',
      is_batch: true,
      batch_kind: 'single_plan_multi_case',
      result: null,
      aggregate: {
        total_children: 2,
        queued_children: 0,
        running_children: 1,
        succeeded_children: 1,
        failed_children: 0,
        cancelled_children: 0,
        completed_children: 1,
        current_child_operation_id: 'op-child-2',
        current_child_plan_id: 'plan-1',
        current_child_case_id: 'case-2',
        current_child_title: 'Case Two',
      },
      children_preview: [
        {
          operation_id: 'op-child-1',
          kind: 'run_case',
          run_type: 'case_run',
          plan_id: 'plan-1',
          case_id: 'case-1',
          title: 'Case One',
          status: 'succeeded',
          verification_verdict: 'passed',
          position_index: 1,
          position_label: '1/2',
          created_at: '2026-01-01T00:00:00Z',
          started_at: '2026-01-01T00:00:01Z',
          finished_at: '2026-01-01T00:00:05Z',
          error_code: null,
          error_message: null,
        },
        {
          operation_id: 'op-child-2',
          kind: 'run_case',
          run_type: 'case_run',
          plan_id: 'plan-1',
          case_id: 'case-2',
          title: 'Case Two',
          status: 'running',
          verification_verdict: null,
          position_index: 2,
          position_label: '2/2',
          created_at: '2026-01-01T00:00:06Z',
          started_at: '2026-01-01T00:00:07Z',
          finished_at: null,
          error_code: null,
          error_message: null,
        },
      ],
    }

    const wrapper = mount(RunDetailPage, {
      global: {
        plugins: [i18n],
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Plan Run Summary')
    expect(wrapper.text()).toContain('Run Context')
    expect(wrapper.text()).toContain('demo-app')
    expect(wrapper.text()).toContain('plan-1')
    expect(wrapper.text()).toContain('Pixel 8')
    expect(wrapper.text()).toContain('Case Runs')
    expect(wrapper.text()).toContain('Case One')
    expect(wrapper.text()).toContain('Case Two')
    expect(wrapper.text()).toContain('Current case')
    expect(wrapper.text()).toContain('case-2')
    expect(wrapper.text()).not.toContain('Evidence')
    expect(wrapper.text()).not.toContain('Artifacts')
  })

  it('renders batch summary and child runs for parent operations', async () => {
    detailState.value = {
      ...detailState.value,
      kind: 'run_plans',
      run_type: 'plan_batch_run',
      title: 'Run 2 plans on emulator-5554',
      case_id: null,
      plan_id: null,
      status: 'running',
      verification_verdict: null,
      result: null,
      is_batch: true,
      batch_kind: 'single_device_multi_plan',
      aggregate: {
        total_children: 2,
        queued_children: 1,
        running_children: 1,
        succeeded_children: 0,
        failed_children: 0,
        cancelled_children: 0,
        completed_children: 0,
        current_child_operation_id: 'op-child-1',
        current_child_plan_id: 'plan-1',
        current_child_title: 'Settings coverage',
      },
      children_preview: [
        {
          operation_id: 'op-child-1',
          kind: 'run_plan',
          run_type: 'plan_run',
          plan_id: 'plan-1',
          title: 'Settings coverage',
          status: 'running',
          verification_verdict: null,
          position_index: 1,
          position_label: '1/2',
          created_at: '2026-01-01T00:00:00Z',
          started_at: '2026-01-01T00:00:01Z',
          finished_at: null,
          error_code: null,
          error_message: null,
        },
        {
          operation_id: 'op-child-2',
          kind: 'run_plan',
          run_type: 'plan_run',
          plan_id: 'plan-2',
          title: 'Checkout coverage',
          status: 'queued',
          verification_verdict: null,
          position_index: 2,
          position_label: '2/2',
          created_at: '2026-01-01T00:00:00Z',
          started_at: null,
          finished_at: null,
          error_code: null,
          error_message: null,
        },
      ],
    }

    const wrapper = mount(RunDetailPage, {
      global: {
        plugins: [i18n],
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Batch Run Summary')
    expect(wrapper.text()).toContain('Run Context')
    expect(wrapper.text()).toContain('demo-app')
    expect(wrapper.text()).toContain('Pixel 8')
    expect(wrapper.text()).toContain('Run 2 plans on emulator-5554')
    expect(wrapper.text()).toContain('Settings coverage')
    expect(wrapper.text()).toContain('Checkout coverage')
    expect(wrapper.text()).toContain('Open Child Run')
    expect(wrapper.text()).toContain('1/2')
    expect(wrapper.text()).toContain('2/2')
    expect(wrapper.text()).not.toContain('Artifacts')
    expect(wrapper.text()).not.toContain('Evidence')
  })

  it('keeps timeline and raw tabs for parent operations', async () => {
    detailState.value = {
      ...detailState.value,
      kind: 'run_plan',
      run_type: 'plan_run',
      case_id: null,
      is_batch: true,
      batch_kind: 'single_plan_multi_case',
      result: null,
      aggregate: {
        total_children: 1,
        queued_children: 0,
        running_children: 1,
        succeeded_children: 0,
        failed_children: 0,
        cancelled_children: 0,
        completed_children: 0,
        current_child_operation_id: 'op-child-1',
        current_child_plan_id: 'plan-1',
        current_child_case_id: 'case-1',
        current_child_title: 'Case One',
      },
    }

    const wrapper = mount(RunDetailPage, {
      global: {
        plugins: [i18n],
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Timeline')
    expect(wrapper.text()).toContain('Raw')
    await wrapper.findAll('button').find((button) => button.text() === 'Timeline')?.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('started')
    await wrapper.findAll('button').find((button) => button.text() === 'Raw')?.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('"batch_kind": "single_plan_multi_case"')
  })

  it('renders optimize summary with field diffs', async () => {
    detailState.value = {
      ...buildDetailState(),
      kind: 'optimize_case',
      run_type: 'optimize_case',
      title: 'Optimize Case One',
      verification_verdict: null,
      result: {
        summary: 'updated judge guidance',
        patched_fields: ['judge_hints'],
        applied: true,
        skip_reason: null,
        confidence: 0.91,
        field_diff_artifact_path: '/tmp/run-1/optimize/field_diffs.json',
        field_diffs: [
          {
            field_name: 'judge_hints',
            reason: 'judge wording was ambiguous',
            before: ['Existing hint'],
            after: ['Clarify end-state wording'],
            changed: true,
          },
        ],
      },
    }
    artifactsState.value = {
      ...artifactsState.value,
      run_type: 'optimize_case',
      status: 'succeeded',
      primary_artifacts: [
        {
          artifact_id: 'field_diffs',
          role: 'field_diffs',
          kind: 'report',
          scope: 'run',
          media_type: 'application/json',
          exists: true,
          label: 'field_diffs',
          case_id: null,
          path: '/tmp/run-1/optimize/field_diffs.json',
          metadata: {},
          content_url: '/v1/runs/op-1/artifacts/field_diffs/content',
          download_url: '/v1/runs/op-1/artifacts/field_diffs/download',
        },
      ],
      artifact_groups: [
        {
          group_id: 'primary',
          title: 'Primary Artifacts',
          items: [
            {
              artifact_id: 'field_diffs',
              role: 'field_diffs',
              kind: 'report',
              scope: 'run',
              media_type: 'application/json',
              exists: true,
              label: 'field_diffs',
              case_id: null,
              path: '/tmp/run-1/optimize/field_diffs.json',
              metadata: {},
              content_url: '/v1/runs/op-1/artifacts/field_diffs/content',
              download_url: '/v1/runs/op-1/artifacts/field_diffs/download',
            },
          ],
        },
      ],
    }

    const wrapper = mount(RunDetailPage, {
      global: {
        plugins: [i18n],
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Optimize Summary')
    expect(wrapper.text()).toContain('Applied')
    expect(wrapper.text()).toContain('judge_hints')
    expect(wrapper.text()).toContain('Clarify end-state wording')
    expect(wrapper.text()).toContain('Existing hint')
    await wrapper.findAll('button').find((button) => button.text() === 'Artifacts')?.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('field_diffs')
    expect(wrapper.text()).toContain('/tmp/run-1/optimize/field_diffs.json')
  })

  it('renders knowledge post-action summary with review link', async () => {
    detailState.value = {
      ...buildDetailState(),
      kind: 'knowledge_post_action',
      run_type: 'knowledge_post_action',
      title: 'Knowledge post action',
      verification_verdict: null,
      result: {
        summary: 'knowledge candidate submitted for pending review',
        submitted: true,
        skip_reason: null,
        candidate_id: 'candidate-1',
      },
    }
    artifactsState.value = {
      ...artifactsState.value,
      run_type: 'knowledge_post_action',
      status: 'succeeded',
    }

    const wrapper = mount(RunDetailPage, {
      global: {
        plugins: [i18n],
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Knowledge Post-Action Summary')
    expect(wrapper.text()).toContain('Candidate Submitted')
    expect(wrapper.text()).toContain('candidate-1')
    expect(wrapper.text()).toContain('Review Candidate')
    expect(wrapper.html()).toContain('/apps/demo-app/knowledge/candidates?candidate_id=candidate-1')
  })

  it('renders skipped knowledge post-action summary with localized skip reason', async () => {
    detailState.value = {
      ...buildDetailState(),
      kind: 'knowledge_post_action',
      run_type: 'knowledge_post_action',
      title: 'Knowledge post action',
      verification_verdict: null,
      result: {
        summary: 'knowledge post action skipped: passed case',
        submitted: false,
        skip_reason: 'verdict_passed',
        candidate_id: null,
      },
    }
    artifactsState.value = {
      ...artifactsState.value,
      run_type: 'knowledge_post_action',
      status: 'succeeded',
    }

    const wrapper = mount(RunDetailPage, {
      global: {
        plugins: [i18n],
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('No Candidate Submitted')
    expect(wrapper.text()).toContain('case passed')
    expect(wrapper.text()).not.toContain('Review Candidate')
  })
})
