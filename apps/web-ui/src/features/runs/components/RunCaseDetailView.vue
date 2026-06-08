<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import RunArtifactPreviewModal from '@/features/runs/components/RunArtifactPreviewModal.vue'
import RunArtifactsPanel from '@/features/runs/components/RunArtifactsPanel.vue'
import RunEvidencePanel from '@/features/runs/components/RunEvidencePanel.vue'
import RunSummaryPanel from '@/features/runs/components/RunSummaryPanel.vue'
import RunTimelinePanel from '@/features/runs/components/RunTimelinePanel.vue'
import {
  flattenArtifacts,
  rawPayload,
  type RunOrchestrationSummaryView,
} from '@/features/runs/lib/runMappers'
import type {
  OperationArtifactsData,
  OperationDetailData,
  OperationEventsData,
} from '@/shared/api/operations'

type TimePresenter = {
  duration: (value: number | null | undefined) => string
  datetime: (value: string | null | undefined) => string | null
  tooltip: (value: string | null | undefined) => string | null
  absolute: (value: string | null | undefined) => string
  relative: (value: string | null | undefined) => string
}

type PlanRunProgressView = {
  totalCases: number
  completedCases: number
  currentCaseId: string | null
  lastCaseId: string | null
  percent: number | null
}

const props = defineProps<{
  operationId: string
  detail: OperationDetailData
  deviceLabel: string
  artifacts: OperationArtifactsData | null | undefined
  events: OperationEventsData | null | undefined
  time: TimePresenter
  resultSummary: string | null
  judgeReason: string | null
  failureHypothesis: string | null
  resultVerdict: string | null
  confidence: number | null
  missingEvidence: string[]
  orchestrationSummary: RunOrchestrationSummaryView | null
  progressSummary: PlanRunProgressView | null
  primaryEvidenceId: string | null
  nextStepSuggestions: string[]
  canReproduce: boolean
}>()

const emit = defineEmits<{
  (event: 'reproduce'): void
}>()

const { t } = useI18n()

const activeTab = ref<'summary' | 'timeline' | 'artifacts' | 'evidence' | 'raw'>('summary')
const selectedPreviewArtifactId = ref<string | null>(null)
const preferredEvidenceId = ref<string | null>(null)

type OptimizeFieldDiffView = {
  field_name: string
  reason: string | null
  before: string[]
  after: string[]
  changed: boolean
}

const allArtifacts = computed(() => flattenArtifacts(props.artifacts))
const optimizeResult = computed<Record<string, unknown> | null>(() => {
  if (props.detail.run_type !== 'optimize_case') {
    return null
  }
  if (!props.detail.result || typeof props.detail.result !== 'object' || Array.isArray(props.detail.result)) {
    return null
  }
  return props.detail.result as Record<string, unknown>
})
const optimizeConfidence = computed<number | null>(() => {
  const value = optimizeResult.value?.confidence
  return typeof value === 'number' ? value : null
})
const optimizeApplied = computed<boolean>(() => optimizeResult.value?.applied === true)
const optimizeSkipReason = computed<string | null>(() => (
  typeof optimizeResult.value?.skip_reason === 'string' ? optimizeResult.value.skip_reason : null
))
const optimizePatchedFields = computed<string[]>(() => (
  Array.isArray(optimizeResult.value?.patched_fields)
    ? optimizeResult.value.patched_fields.filter((item): item is string => typeof item === 'string' && item.length > 0)
    : []
))
const optimizeFieldDiffs = computed<OptimizeFieldDiffView[]>(() => {
  const raw = optimizeResult.value?.field_diffs
  if (!Array.isArray(raw)) {
    return []
  }
  return raw.flatMap((item) => {
    if (!item || typeof item !== 'object' || Array.isArray(item)) {
      return []
    }
    const record = item as Record<string, unknown>
    const fieldName = typeof record.field_name === 'string' ? record.field_name : null
    if (!fieldName) {
      return []
    }
    const toStringList = (value: unknown): string[] => (
      Array.isArray(value)
        ? value.filter((entry): entry is string => typeof entry === 'string' && entry.length > 0)
        : []
    )
    return [{
      field_name: fieldName,
      reason: typeof record.reason === 'string' ? record.reason : null,
      before: toStringList(record.before),
      after: toStringList(record.after),
      changed: record.changed === true,
    }]
  })
})
const selectedPreviewArtifact = computed(() => {
  if (!selectedPreviewArtifactId.value) {
    return null
  }
  return allArtifacts.value.find((item) => item.artifact_id === selectedPreviewArtifactId.value) ?? null
})

watch(allArtifacts, (items) => {
  if (!selectedPreviewArtifactId.value) {
    return
  }
  if (items.some((item) => item.artifact_id === selectedPreviewArtifactId.value)) {
    return
  }
  selectedPreviewArtifactId.value = null
}, { immediate: true })

function openArtifactPreview(artifactId: string) {
  selectedPreviewArtifactId.value = artifactId
}

function closeArtifactPreview() {
  selectedPreviewArtifactId.value = null
}

function openEvidenceTab(evidenceId: string) {
  preferredEvidenceId.value = evidenceId
  activeTab.value = 'evidence'
}

function formatList(items: string[]) {
  return items.length > 0 ? items.join(' | ') : '-'
}
</script>

<template>
  <div class="tab-row">
    <button type="button" class="tab-button" :class="{ active: activeTab === 'summary' }" @click="activeTab = 'summary'">{{ t('runDetail.tabs.summary') }}</button>
    <button type="button" class="tab-button" :class="{ active: activeTab === 'timeline' }" @click="activeTab = 'timeline'">{{ t('runDetail.tabs.timeline') }}</button>
    <button type="button" class="tab-button" :class="{ active: activeTab === 'artifacts' }" @click="activeTab = 'artifacts'">{{ t('runDetail.tabs.artifacts') }}</button>
    <button type="button" class="tab-button" :class="{ active: activeTab === 'evidence' }" @click="activeTab = 'evidence'">{{ t('runDetail.tabs.evidence') }}</button>
    <button type="button" class="tab-button" :class="{ active: activeTab === 'raw' }" @click="activeTab = 'raw'">{{ t('runDetail.tabs.raw') }}</button>
  </div>

  <div v-if="activeTab === 'summary'" class="summary-tab">
    <section v-if="optimizeResult" class="optimize-card">
      <div class="optimize-head">
        <strong>{{ t('runDetail.optimize.title') }}</strong>
        <span class="optimize-badge" :class="{ applied: optimizeApplied, skipped: !optimizeApplied }">
          {{ optimizeApplied ? t('runDetail.optimize.applied') : t('runDetail.optimize.skipped') }}
        </span>
      </div>
      <div class="optimize-grid">
        <div class="optimize-item">
          <span class="optimize-label">{{ t('runDetail.fields.confidence') }}</span>
          <strong>{{ optimizeConfidence == null ? '-' : optimizeConfidence }}</strong>
        </div>
        <div class="optimize-item">
          <span class="optimize-label">{{ t('runDetail.optimize.skipReason') }}</span>
          <strong>
            {{
              optimizeSkipReason
                ? t(`runDetail.optimize.skipReasons.${optimizeSkipReason}`)
                : '-'
            }}
          </strong>
        </div>
        <div class="optimize-item optimize-item-full">
          <span class="optimize-label">{{ t('runDetail.optimize.patchedFields') }}</span>
          <strong>{{ optimizePatchedFields.length > 0 ? optimizePatchedFields.join(', ') : '-' }}</strong>
        </div>
      </div>
      <div class="optimize-diff-list">
        <div v-if="optimizeFieldDiffs.length === 0" class="optimize-empty">
          {{ t('runDetail.optimize.emptyDiffs') }}
        </div>
        <div v-for="item in optimizeFieldDiffs" :key="item.field_name" class="optimize-diff-item">
          <div class="optimize-diff-head">
            <strong>{{ item.field_name }}</strong>
            <span class="optimize-diff-status">
              {{ item.changed ? t('runDetail.optimize.changed') : t('runDetail.optimize.unchanged') }}
            </span>
          </div>
          <p v-if="item.reason" class="optimize-reason">{{ item.reason }}</p>
          <div class="optimize-diff-body">
            <div class="optimize-item">
              <span class="optimize-label">{{ t('runDetail.optimize.before') }}</span>
              <strong>{{ formatList(item.before) }}</strong>
            </div>
            <div class="optimize-item">
              <span class="optimize-label">{{ t('runDetail.optimize.after') }}</span>
              <strong>{{ formatList(item.after) }}</strong>
            </div>
          </div>
        </div>
      </div>
    </section>

    <RunSummaryPanel
      :detail="detail"
      :device-label="deviceLabel"
      :time="time"
      :result-summary="resultSummary"
      :judge-reason="judgeReason"
      :failure-hypothesis="failureHypothesis"
      :result-verdict="resultVerdict"
      :confidence="confidence"
      :missing-evidence="missingEvidence"
      :orchestration-summary="orchestrationSummary"
      :progress-summary="progressSummary"
      :primary-evidence-id="primaryEvidenceId"
      :next-step-suggestions="nextStepSuggestions"
      :can-reproduce="canReproduce"
      @open-evidence="openEvidenceTab"
      @reproduce="emit('reproduce')"
    />
  </div>

  <RunTimelinePanel
    v-else-if="activeTab === 'timeline'"
    :items="events?.items ?? []"
    :time="time"
  />

  <RunArtifactsPanel
    v-else-if="activeTab === 'artifacts'"
    :operation-id="operationId"
    :artifacts="artifacts"
    @preview-artifact="openArtifactPreview"
  />

  <RunEvidencePanel
    v-else-if="activeTab === 'evidence'"
    :operation-id="operationId"
    :detail="detail"
    :artifacts="artifacts"
    :preferred-evidence-id="preferredEvidenceId"
  />

  <div v-else class="raw-panel">
    <pre>{{ rawPayload(detail) }}</pre>
  </div>

  <RunArtifactPreviewModal
    v-if="selectedPreviewArtifact"
    :operation-id="operationId"
    :artifact="selectedPreviewArtifact"
    @close="closeArtifactPreview"
  />
</template>

<style scoped>
.tab-row,
.raw-panel,
.summary-tab,
.optimize-card,
.optimize-grid,
.optimize-diff-list,
.optimize-diff-body {
  display: grid;
  gap: 12px;
}

.tab-row {
  grid-template-columns: repeat(5, minmax(0, 1fr));
}

.tab-button {
  min-height: 38px;
  padding: 0 14px;
  border-radius: 8px;
  font: inherit;
  border: 1px solid var(--border-default);
  background: var(--surface-default);
  color: var(--text-primary);
}

.tab-button.active {
  border-color: var(--accent-primary);
  color: var(--accent-primary);
}

.optimize-card {
  padding: 16px;
  border-radius: 12px;
  border: 1px solid var(--border-muted);
  background: var(--surface-subtle);
}

.optimize-head,
.optimize-diff-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.optimize-grid,
.optimize-diff-body {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.optimize-item,
.optimize-diff-item {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.optimize-item-full {
  grid-column: 1 / -1;
}

.optimize-label,
.optimize-reason,
.optimize-empty,
.optimize-diff-status {
  color: var(--text-secondary);
}

.optimize-badge {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 0.82rem;
}

.optimize-badge.applied {
  color: var(--status-success-text);
  background: var(--status-success-bg);
}

.optimize-badge.skipped {
  color: var(--status-warning-text);
  background: var(--status-warning-bg);
}

.optimize-diff-item {
  padding-top: 12px;
  border-top: 1px solid var(--border-default);
}

pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
  overflow-x: auto;
  max-width: 100%;
}

@media (max-width: 880px) {
  .tab-row {
    grid-template-columns: 1fr;
  }

  .optimize-grid,
  .optimize-diff-body {
    grid-template-columns: 1fr;
  }
}
</style>
