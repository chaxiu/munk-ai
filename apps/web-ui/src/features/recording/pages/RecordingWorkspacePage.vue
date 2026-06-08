<script setup lang="ts">
import { CirclePlay, Clapperboard, FileOutput, Play, Sparkles, Square, TestTube2 } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { useAppsQuery } from '@/features/apps/queries/useAppsQuery'
import AnalysisProgressModal from '@/features/recording/components/AnalysisProgressModal.vue'
import RecordingStatusPanel from '@/features/recording/components/RecordingStatusPanel.vue'
import ScrcpySurface from '@/features/recording/components/ScrcpySurface.vue'
import { useRecordingDeviceSelection } from '@/features/recording/composables/useRecordingDeviceSelection'
import { useRecordingWorkspaceController } from '@/features/recording/composables/useRecordingWorkspaceController'
import type { InteractionPayload } from '@/shared/api/recording.types'
import type { ForwardingAckRequest } from '@/shared/api/recording'
import AppCard from '@/shared/components/AppCard.vue'
import UiButton from '@/shared/ui/UiButton.vue'
import UiSelect from '@/shared/ui/UiSelect.vue'

const { t } = useI18n()

const appId = ref('')
const {
  selectedDeviceRef,
  deviceOptions,
  devicesLoading,
  errorMessage: deviceErrorMessage,
} = useRecordingDeviceSelection()
const {
  session,
  events,
  timeline,
  analysis,
  exportedCase,
  replayResult,
  bridge,
  loading: controllerLoading,
  errorMessage,
  successMessage,
  analysisModalOpen,
  analysisEvents,
  analysisProgressError,
  analysisOperation,
  createSession: submitCreateSession,
  beginSession: submitBeginSession,
  stopSession: submitStopSession,
  analyzeSession: submitAnalyzeSession,
  exportCase: submitExportCase,
  replayCase: submitReplayCase,
  closeAnalysisModal,
  handleAnalysisExport,
  handleInteractionForwarded,
} = useRecordingWorkspaceController()
const appsQuery = useAppsQuery(computed(() => ({ platform: 'android' })))

const loading = computed(() => controllerLoading.value || appsQuery.isFetching.value)
const appOptions = computed(() => (
  (appsQuery.data.value ?? []).map((item) => ({
    label: item.entry_identity ? `${item.app_id} (${item.entry_identity})` : item.app_id,
    value: item.app_id,
  }))
))
const selectedApp = computed(() =>
  (appsQuery.data.value ?? []).find((item) => item.app_id === appId.value) ?? null
)
const entryIdentity = computed(() => selectedApp.value?.entry_identity?.trim() ?? '')
const resolvedErrorMessage = computed(() => errorMessage.value ?? deviceErrorMessage.value)

const canBegin = computed(() => session.value?.status === 'created' && !loading.value)
const canStop = computed(() => session.value?.status === 'recording' && !loading.value)
const canAnalyze = computed(() => ['stopped', 'cancelled', 'failed'].includes(session.value?.status ?? '') && !loading.value)
const canExport = computed(() => Boolean(analysis.value?.export_ready) && !loading.value)
const canReplay = computed(() => {
  if (loading.value) {
    return false
  }
  if (analysis.value?.test_case) {
    return true
  }
  return ['stopped', 'cancelled'].includes(session.value?.status ?? '')
})
const canCreateSession = computed(() => (
  !loading.value
  && Boolean(selectedDeviceRef.value)
  && Boolean(appId.value)
  && Boolean(entryIdentity.value)
))

async function createSession() {
  if (!canCreateSession.value) {
    return
  }
  await submitCreateSession({
    appId: appId.value,
    entryIdentity: entryIdentity.value,
    deviceRef: selectedDeviceRef.value || undefined,
  })
}

async function beginSession() {
  if (!canBegin.value) {
    return
  }
  await submitBeginSession()
}

async function stopSession() {
  if (!canStop.value) {
    return
  }
  await submitStopSession()
}

async function analyzeSession() {
  if (!canAnalyze.value) {
    return
  }
  await submitAnalyzeSession()
}

async function exportCase() {
  if (!canExport.value) {
    return
  }
  await submitExportCase()
}

async function replayCase() {
  if (!canReplay.value) {
    return
  }
  await submitReplayCase()
}

function formatTargetSummary(target: {
  label?: string | null
  kind?: string | null
  confidence?: number | null
} | null | undefined): string {
  if (!target) {
    return 'none'
  }
  const parts = [
    target.label ?? 'unlabeled',
    target.kind ? `(${target.kind})` : null,
    target.confidence != null ? `confidence=${target.confidence}` : null,
  ].filter(Boolean)
  return parts.join(' ')
}

function formatIdentity(value: string | null | undefined): string {
  return value?.trim() || 'none'
}

async function onInteractionForwarded(payload: {
  interaction: InteractionPayload
  ack: ForwardingAckRequest
}) {
  await handleInteractionForwarded(payload)
}
</script>

<template>
  <section class="app-page box-border h-[calc(100vh-3.5rem)] min-h-[calc(100vh-3.5rem)] overflow-hidden">
    <div class="grid h-full min-h-0 items-stretch gap-4 xl:grid-cols-[minmax(0,1.5fr)_minmax(360px,420px)]">
      <AppCard class="flex h-full min-h-0 flex-col gap-4 overflow-hidden">
        <div class="flex items-center justify-between gap-4">
          <div class="flex flex-none items-center gap-2">
            <div class="w-40">
              <UiSelect
                v-model="selectedDeviceRef"
                :options="deviceOptions"
                :disabled="devicesLoading"
                :placeholder="t('recording.selectAndroidDevice')"
              />
            </div>
            <div class="w-40">
              <UiSelect
                v-model="appId"
                :options="appOptions"
                :disabled="appsQuery.isFetching.value"
                :placeholder="t('recording.selectAndroidApp')"
              />
            </div>
          </div>
          <div class="flex shrink-0 flex-wrap items-center justify-end gap-2">
            <UiButton size="sm" variant="primary" :disabled="!canCreateSession" @click="createSession">
              <Clapperboard class="h-4 w-4" />
              {{ t('recording.createSession') }}
            </UiButton>
            <UiButton size="sm" variant="primary" :disabled="!canBegin" @click="beginSession">
              <Play class="h-4 w-4" />
              {{ t('recording.begin') }}
            </UiButton>
            <UiButton size="sm" :disabled="!canStop" @click="stopSession">
              <Square class="h-4 w-4" />
              {{ t('recording.stop') }}
            </UiButton>
          </div>
        </div>

        <div v-if="resolvedErrorMessage" class="rounded-lg border border-error-text/20 bg-error-bg px-4 py-3 text-sm text-error-text">
          {{ resolvedErrorMessage }}
        </div>
        <div v-if="successMessage" class="rounded-lg border border-success-text/20 bg-success-bg px-4 py-3 text-sm text-success-text">
          {{ successMessage }}
        </div>

        <div class="relative min-h-0 flex-1 overflow-hidden rounded-lg bg-surface-muted">
          <ScrcpySurface
            v-if="bridge?.ws_url"
            :ws-url="bridge.ws_url"
            @interaction-forwarded="onInteractionForwarded"
          />
          <div v-else class="flex h-full min-h-[520px] w-full items-center justify-center bg-[radial-gradient(circle_at_top,rgba(37,99,235,0.08),transparent_40%)] p-6">
            <div class="grid max-w-sm gap-3 rounded-xl border border-dashed border-border-strong bg-surface-default p-8 text-center">
              <CirclePlay class="mx-auto h-8 w-8 text-text-muted" />
              <h2 class="text-base font-semibold text-text-primary">{{ t('recording.beginViewer') }}</h2>
              <p class="text-sm leading-6 text-text-secondary">
                {{ t('recording.beginViewerHint') }}
              </p>
            </div>
          </div>
        </div>
      </AppCard>

      <aside class="flex h-full min-h-0 flex-col gap-4 overflow-hidden">
        <AppCard class="grid shrink-0 gap-5">
          <div class="flex items-start gap-3">
            <div class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-border-muted bg-surface-muted text-text-secondary">
              <Sparkles class="h-4 w-4" />
            </div>
            <div class="grid gap-1">
              <span class="text-[11px] font-semibold tracking-[0.16em] text-text-muted">
                {{ t('recording.postProcessing.title') }}
              </span>
              <h2 class="text-base font-semibold text-text-primary">{{ t('recording.analysis') }}</h2>
            </div>
          </div>
          <div class="grid gap-2 sm:grid-cols-3">
            <UiButton size="sm" block :disabled="!canAnalyze" @click="analyzeSession">
              <Sparkles class="h-4 w-4" />
              {{ t('recording.analyze') }}
            </UiButton>
            <UiButton size="sm" block :disabled="!canExport" @click="exportCase">
              <FileOutput class="h-4 w-4" />
              {{ t('recording.exportCase') }}
            </UiButton>
            <UiButton size="sm" block :disabled="!canReplay" @click="replayCase">
              <TestTube2 class="h-4 w-4" />
              {{ t('recording.replayCase') }}
            </UiButton>
          </div>
        </AppCard>

        <div class="min-h-0 flex-1 overflow-y-auto pr-1 scrollbar-subtle">
          <div class="grid content-start gap-4">
            <RecordingStatusPanel :session="session" :events="events" :timeline="timeline" />

            <AppCard v-if="analysis || exportedCase || replayResult" class="grid gap-5">
              <header class="grid gap-2">
                <div class="inline-flex items-center gap-2 text-[11px] font-semibold tracking-[0.16em] text-text-muted">
                  <Sparkles class="h-4 w-4" />
                  {{ t('recording.resultsBadge') }}
                </div>
                <h2 class="text-lg font-semibold text-text-primary">{{ t('recording.resultsTitle') }}</h2>
              </header>

              <div class="grid gap-4">
                <div v-if="analysis" class="grid gap-4 rounded-lg border border-border-muted bg-surface-muted p-3">
                  <div class="flex items-center justify-between gap-3 border-b border-border-muted pb-3">
                    <h3 class="text-sm font-semibold text-text-primary">{{ t('recording.analysisResult') }}</h3>
                    <span class="inline-flex rounded-full bg-surface-default px-2.5 py-1 text-xs font-semibold text-text-secondary">{{ analysis.status }}</span>
                  </div>
                  <div class="grid gap-3">
                    <div v-if="analysis.source_summary" class="grid gap-1">
                      <label class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('recording.fields.source') }}</label>
                      <span class="text-sm text-text-primary">{{ analysis.source_summary }}</span>
                    </div>
                    <div v-if="analysis.failure_reason" class="grid gap-1">
                      <label class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('recording.fields.failure') }}</label>
                      <span class="text-sm text-error-text">{{ analysis.failure_reason }}</span>
                    </div>
                  </div>

                  <div v-if="analysis.test_case" class="grid gap-4 rounded-lg border border-border bg-surface-default p-3">
                    <h4 class="text-base font-semibold text-text-primary">{{ analysis.test_case.title }}</h4>
                    <div class="grid gap-3">
                      <div class="grid gap-1">
                        <label class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('recording.fields.intent') }}</label>
                        <span class="text-sm text-text-primary">{{ analysis.test_case.intent }}</span>
                      </div>
                      <div class="grid gap-1">
                        <label class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('recording.fields.runnerGoal') }}</label>
                        <span class="text-sm text-text-primary">{{ analysis.test_case.runner_goal }}</span>
                      </div>
                    </div>

                    <div class="grid gap-2">
                      <label class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('recording.fields.procedure') }}</label>
                      <ol class="grid gap-2">
                        <li
                          v-for="(step, index) in analysis.test_case.procedure"
                          :key="step"
                          class="flex gap-3 rounded-lg border border-border-muted bg-surface-muted px-3 py-2"
                        >
                          <span class="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent-soft text-xs font-semibold text-accent">{{ index + 1 }}</span>
                          <span class="text-sm text-text-primary">{{ step }}</span>
                        </li>
                      </ol>
                    </div>

                    <div class="grid gap-2">
                      <label class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('recording.fields.expected') }}</label>
                      <ul class="grid gap-2">
                        <li
                          v-for="item in analysis.test_case.expected"
                          :key="item"
                          class="rounded-lg border border-border-muted bg-surface-muted px-3 py-2 text-sm text-text-primary"
                        >
                          {{ item }}
                        </li>
                      </ul>
                    </div>
                  </div>

                  <div v-if="(analysis.steps ?? []).length > 0" class="grid gap-3 rounded-lg border border-border bg-surface-default p-3">
                    <div class="flex items-center justify-between gap-3">
                      <h4 class="text-base font-semibold text-text-primary">Analysis Evidence</h4>
                      <span class="text-xs font-medium uppercase tracking-[0.16em] text-text-muted">debug</span>
                    </div>
                    <details
                      v-for="step in analysis.steps ?? []"
                      :key="`${step.entry_id}-${step.seq}`"
                      class="rounded-lg border border-border-muted bg-surface-muted"
                    >
                      <summary class="flex cursor-pointer list-none items-center justify-between gap-3 px-3 py-2 text-sm text-text-primary">
                        <span class="font-medium">Step {{ step.seq }} · {{ step.kind }}</span>
                        <span class="text-text-secondary">{{ step.procedure_step ?? step.summary ?? 'none' }}</span>
                      </summary>
                      <div class="grid gap-3 border-t border-border-muted px-3 py-3">
                        <div class="grid gap-1">
                          <label class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">Intent</label>
                          <span class="text-sm text-text-primary">{{ step.intent ?? 'none' }}</span>
                        </div>
                        <div class="grid gap-1">
                          <label class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">Action</label>
                          <span class="text-sm text-text-primary">{{ step.action ?? 'none' }}</span>
                        </div>
                        <div class="grid gap-1">
                          <label class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">Procedure</label>
                          <span class="text-sm text-text-primary">{{ step.procedure_step ?? 'none' }}</span>
                        </div>
                        <div class="grid gap-1">
                          <label class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">State Change</label>
                          <span class="text-sm text-text-primary">{{ step.state_change ?? 'none' }}</span>
                        </div>
                        <div class="grid gap-2 md:grid-cols-2">
                          <div class="grid gap-1">
                            <label class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">Page Identity</label>
                            <span class="text-sm text-text-primary">
                              before={{ formatIdentity(step.action_evidence?.before_entry_identity ?? step.outcome_evidence?.before_entry_identity) }}
                            </span>
                            <span class="text-sm text-text-primary">
                              after={{ formatIdentity(step.action_evidence?.after_entry_identity ?? step.outcome_evidence?.after_entry_identity) }}
                            </span>
                            <span class="text-sm text-text-secondary">
                              surface(before/after)=
                              {{ formatIdentity(step.action_evidence?.before_surface_identity ?? step.outcome_evidence?.before_surface_identity) }}
                              /
                              {{ formatIdentity(step.action_evidence?.after_surface_identity ?? step.outcome_evidence?.after_surface_identity) }}
                            </span>
                          </div>
                          <div class="grid gap-1">
                            <label class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">Resolved Target</label>
                            <span class="text-sm text-text-primary">{{ formatTargetSummary(step.action_evidence?.resolved_target) }}</span>
                            <span class="text-sm text-text-secondary">{{ step.action_evidence?.raw_action_summary ?? 'none' }}</span>
                          </div>
                        </div>
                        <div class="grid gap-1">
                          <label class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">Target Candidates</label>
                          <ul class="grid gap-2">
                            <li
                              v-for="candidate in step.action_evidence?.target_candidates ?? []"
                              :key="`${step.entry_id}-${candidate.rank}-${candidate.label ?? 'candidate'}`"
                              class="rounded-md border border-border-muted bg-surface-default px-3 py-2 text-sm text-text-primary"
                            >
                              #{{ candidate.rank }} {{ formatTargetSummary(candidate) }}
                            </li>
                          </ul>
                          <span v-if="!(step.action_evidence?.target_candidates?.length)" class="text-sm text-text-secondary">none</span>
                        </div>
                        <div class="grid gap-1">
                          <label class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">Outcome Diff</label>
                          <span class="text-sm text-text-primary">{{ step.outcome_evidence?.screen_diff_summary ?? 'none' }}</span>
                        </div>
                        <div v-if="(step.warnings ?? []).length > 0" class="grid gap-1 rounded-md border border-warning-text/20 bg-warning-bg px-3 py-2">
                          <label class="text-xs font-semibold uppercase tracking-[0.18em] text-warning-text">{{ t('recording.fields.warnings') }}</label>
                          <ul class="grid gap-1 text-sm text-warning-text">
                            <li v-for="warning in step.warnings ?? []" :key="warning">{{ warning }}</li>
                          </ul>
                        </div>
                      </div>
                    </details>
                  </div>

                  <div v-if="(analysis.warnings ?? []).length > 0" class="grid gap-2 rounded-lg border border-warning-text/20 bg-warning-bg p-3 text-warning-text">
                    <label class="text-xs font-semibold uppercase tracking-[0.18em]">{{ t('recording.fields.warnings') }}</label>
                    <ul class="grid gap-2 text-sm">
                      <li v-for="warning in analysis.warnings ?? []" :key="warning">{{ warning }}</li>
                    </ul>
                  </div>
                </div>

                <div v-if="exportedCase" class="grid gap-3 rounded-lg border border-border-muted bg-surface-muted p-3">
                  <div class="flex items-center justify-between gap-3 border-b border-border-muted pb-3">
                    <h3 class="text-sm font-semibold text-text-primary">{{ t('recording.export') }}</h3>
                  </div>
                  <div class="grid gap-3">
                    <div class="grid gap-1">
                      <label class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('recording.fields.caseId') }}</label>
                      <span class="text-sm text-text-primary">{{ exportedCase.case_id }}</span>
                    </div>
                    <div v-if="exportedCase.plan_id" class="grid gap-1">
                      <label class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('recording.fields.planId') }}</label>
                      <span class="text-sm text-text-primary">{{ exportedCase.plan_id }}</span>
                    </div>
                    <div class="grid gap-1">
                      <label class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('recording.fields.casePath') }}</label>
                      <span class="break-all text-sm text-text-primary">{{ exportedCase.case_path }}</span>
                    </div>
                    <div v-if="exportedCase.plan_path" class="grid gap-1">
                      <label class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('recording.fields.planPath') }}</label>
                      <span class="break-all text-sm text-text-primary">{{ exportedCase.plan_path }}</span>
                    </div>
                    <div class="grid gap-1">
                      <label class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('recording.fields.analysisPath') }}</label>
                      <span class="break-all text-sm text-text-primary">{{ exportedCase.analysis_path }}</span>
                    </div>
                  </div>
                  <RouterLink
                    v-if="exportedCase.plan_id"
                    class="inline-flex min-h-9 items-center justify-center rounded-md border border-border bg-surface-default px-3 text-sm font-medium text-text-primary transition-colors hover:border-border-strong hover:bg-surface-default"
                    :to="`/tests/plans/${encodeURIComponent(session?.app_id ?? appId)}/${encodeURIComponent(exportedCase.plan_id)}`"
                  >
                    {{ t('recording.openTestsPlan') }}
                  </RouterLink>
                </div>

                <div v-if="replayResult" class="grid gap-3 rounded-lg border border-border-muted bg-surface-muted p-3">
                  <div class="flex items-center justify-between gap-3 border-b border-border-muted pb-3">
                    <h3 class="text-sm font-semibold text-text-primary">{{ t('recording.replay') }}</h3>
                    <span
                      class="inline-flex rounded-full px-2.5 py-1 text-xs font-semibold"
                      :class="replayResult.verdict === 'passed' ? 'bg-success-bg text-success-text' : 'bg-error-bg text-error-text'"
                    >
                      {{ replayResult.verdict }}
                    </span>
                  </div>
                  <div class="grid gap-3">
                    <div class="grid gap-1">
                      <label class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('recording.fields.operationId') }}</label>
                      <span class="text-sm text-text-primary">{{ replayResult.operation_id }}</span>
                    </div>
                    <div class="grid gap-1">
                      <label class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('recording.fields.runDir') }}</label>
                      <span class="break-all text-sm text-text-primary">{{ replayResult.run_dir }}</span>
                    </div>
                    <div class="grid gap-1">
                      <label class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('recording.fields.resultPath') }}</label>
                      <span class="break-all text-sm text-text-primary">{{ replayResult.result_path }}</span>
                    </div>
                  </div>
                  <RouterLink class="inline-flex min-h-9 items-center justify-center rounded-md border border-border bg-surface-default px-3 text-sm font-medium text-text-primary transition-colors hover:border-border-strong hover:bg-surface-default" :to="`/runs/${encodeURIComponent(replayResult.operation_id)}`">
                    {{ t('recording.openRunDetail') }}
                  </RouterLink>
                </div>
              </div>
            </AppCard>
          </div>
        </div>
      </aside>
    </div>
  </section>
  <AnalysisProgressModal
    :open="analysisModalOpen"
    :operation="analysisOperation"
    :events="analysisEvents"
    :error-message="analysisProgressError"
    :can-export="Boolean(analysis?.export_ready)"
    @close="closeAnalysisModal"
    @retry="analyzeSession"
    @export="handleAnalysisExport"
  />
</template>
