<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'

import AppBadge from '@/shared/components/AppBadge.vue'
import AppCard from '@/shared/components/AppCard.vue'
import AppEmptyState from '@/shared/components/AppEmptyState.vue'
import RunCaseDetailView from '@/features/runs/components/RunCaseDetailView.vue'
import RunParentDetailView from '@/features/runs/components/RunParentDetailView.vue'
import { formatDeviceLabel } from '@/features/devices/deviceLabels'
import { useDevicesQuery } from '@/features/devices/queries/useDevicesQuery'
import { LocalApiClientError } from '@/shared/api/client'
import { useTime } from '@/shared/time/useTime'
import {
  cancelOperation,
  reproduceOperation,
} from '@/shared/api/operations'
import { translateErrorCode } from '@/shared/i18n/errorMessages'
import {
  displayRunTitle,
  isTerminalStatus,
  planRunProgress,
  runCaseResult,
  runOrchestrationSummary,
  statusTone,
  verdictTone,
} from '@/features/runs/lib/runMappers'
import { useRunArtifactsQuery } from '@/features/runs/queries/useRunArtifactsQuery'
import { useRunDetailQuery } from '@/features/runs/queries/useRunDetailQuery'
import { useRunEventsQuery } from '@/features/runs/queries/useRunEventsQuery'

const route = useRoute()
const { t } = useI18n()
const time = useTime({ relative: true })

const operationId = computed(() => String(route.params.operationId))
const actionMessage = ref<string | null>(null)
const actionError = ref<string | null>(null)
const devicesQuery = useDevicesQuery('all')

const detailQuery = useRunDetailQuery(operationId)
const artifactsQuery = useRunArtifactsQuery(operationId)
const eventsQuery = useRunEventsQuery(operationId, computed(() => !isTerminalStatus(detailQuery.data.value?.status)))

const detail = computed(() => detailQuery.data.value)
const resultData = computed(() => runCaseResult(detail.value))
const orchestrationSummary = computed(() => runOrchestrationSummary(detail.value))
const progressSummary = computed(() => planRunProgress(detail.value))
const isBatchRun = computed(() => Boolean(detail.value?.is_batch))
const artifacts = computed(() => artifactsQuery.data.value)
const resultSummary = computed(() => typeof resultData.value?.summary === 'string' ? resultData.value.summary : null)
const judgeReason = computed(() => typeof resultData.value?.judge_reason === 'string' ? resultData.value.judge_reason : null)
const failureHypothesis = computed(() => (
  typeof resultData.value?.failure_hypothesis === 'string' ? resultData.value.failure_hypothesis : null
))
const resultVerdict = computed(() => (
  typeof resultData.value?.verdict === 'string' ? resultData.value.verdict : detail.value?.verification_verdict ?? null
))
const confidence = computed(() => typeof resultData.value?.confidence === 'number' ? resultData.value.confidence : null)
const missingEvidence = computed(() => (
  Array.isArray(resultData.value?.missing_evidence)
    ? resultData.value.missing_evidence.filter((item): item is string => typeof item === 'string' && item.length > 0)
    : []
))
const supportingEvidenceIds = computed(() => (
  Array.isArray(resultData.value?.supporting_evidence_ids)
    ? resultData.value.supporting_evidence_ids.filter((item): item is string => typeof item === 'string' && item.length > 0)
    : []
))
const primaryEvidenceId = computed(() => supportingEvidenceIds.value[0] ?? null)
const canReproduceFromSummary = computed(() => !isBatchRun.value)
const deviceLabel = computed(() => (
  formatDeviceLabel(detail.value?.device_ref, devicesQuery.data.value ?? [], '-')
))
const nextStepSuggestions = computed(() => {
  const suggestions: string[] = []
  if (detail.value && !isTerminalStatus(detail.value.status)) {
    suggestions.push(t('runDetail.summary.suggestions.waitForCompletion'))
  }
  if (resultVerdict.value === 'failed' && primaryEvidenceId.value) {
    suggestions.push(t('runDetail.summary.suggestions.reviewPrimaryEvidence'))
  } else if (resultVerdict.value === 'failed' && (failureHypothesis.value || judgeReason.value || resultSummary.value)) {
    suggestions.push(t('runDetail.summary.suggestions.reviewFailureReason'))
  }
  if (missingEvidence.value.length > 0) {
    suggestions.push(t('runDetail.summary.suggestions.fillMissingEvidence'))
  }
  if (resultVerdict.value === 'passed') {
    suggestions.push(t('runDetail.summary.suggestions.archivePassedRun'))
  }
  return suggestions.length > 0 ? suggestions : [t('runDetail.summary.suggestions.inspectArtifacts')]
})

const errorMessage = computed(() => {
  const error = detailQuery.error.value ?? artifactsQuery.error.value ?? eventsQuery.error.value
  if (!error) {
    return null
  }
  if (error instanceof LocalApiClientError) {
    return translateErrorCode(error.code, error.message)
  }
  if (error instanceof Error) {
    return error.message
  }
  return String(error)
})

async function handleRefresh() {
  actionMessage.value = null
  actionError.value = null
  await Promise.all([
    detailQuery.refetch(),
    artifactsQuery.refetch(),
    eventsQuery.refetch(),
  ])
}

async function handleCancel() {
  actionMessage.value = null
  actionError.value = null
  try {
    const response = await cancelOperation(operationId.value)
    actionMessage.value = t('runDetail.messages.cancelRequested', { status: response.status })
    await handleRefresh()
  } catch (error) {
    if (error instanceof LocalApiClientError) {
      actionError.value = translateErrorCode(error.code, error.message)
    } else if (error instanceof Error) {
      actionError.value = error.message
    } else {
      actionError.value = String(error)
    }
  }
}

async function handleReproduce() {
  actionMessage.value = null
  actionError.value = null
  try {
    const response = await reproduceOperation(operationId.value)
    actionMessage.value = t('runDetail.messages.reproduceReady', { count: response.reproduction_entries?.length ?? 0 })
    await handleRefresh()
  } catch (error) {
    if (error instanceof LocalApiClientError) {
      actionError.value = translateErrorCode(error.code, error.message)
    } else if (error instanceof Error) {
      actionError.value = error.message
    } else {
      actionError.value = String(error)
    }
  }
}
</script>

<template>
  <section class="page page-padded">
    <AppCard>
      <div class="header-row">
        <div class="header-main">
          <h2>{{ detail ? displayRunTitle(detail) : operationId }}</h2>
        </div>
        <div class="actions">
          <button type="button" class="secondary-button" @click="handleRefresh">{{ t('common.refresh') }}</button>
          <button
            v-if="!isBatchRun"
            type="button"
            class="secondary-button"
            @click="handleReproduce"
          >
            {{ t('runDetail.actions.reproduce') }}
          </button>
          <button
            v-if="detail && !isTerminalStatus(detail.status)"
            type="button"
            class="danger-button"
            @click="handleCancel"
          >
            {{ t('runDetail.actions.cancel') }}
          </button>
        </div>
      </div>
      <p v-if="actionMessage" class="success-text">{{ actionMessage }}</p>
      <p v-if="actionError" class="error-text">{{ actionError }}</p>
      <p v-if="detailQuery.isFetching.value && !detail" class="muted">{{ t('common.loading') }}</p>
      <AppEmptyState v-else-if="errorMessage" :title="t('runDetail.errorTitle')" :description="errorMessage" />
      <template v-else-if="detail">
        <div class="badge-row">
          <AppBadge>{{ detail.run_type ? t(`runs.types.${detail.run_type}`) : detail.kind }}</AppBadge>
          <AppBadge :tone="statusTone(detail.status)">{{ t(`runs.status.${detail.status}`) }}</AppBadge>
          <AppBadge v-if="detail.verification_verdict" :tone="verdictTone(detail.verification_verdict)">
            {{ t(`runs.verdict.${detail.verification_verdict}`) }}
          </AppBadge>
          <AppBadge v-if="detail.phase === 'planned'" tone="warning">{{ t('runs.phase.planned') }}</AppBadge>
        </div>
      </template>
    </AppCard>

    <AppCard v-if="detail">
      <RunParentDetailView
        v-if="isBatchRun"
        :detail="detail"
        :device-label="deviceLabel"
        :events="eventsQuery.data.value"
        :time="time"
      />
      <RunCaseDetailView
        v-else
        :operation-id="operationId"
        :detail="detail"
        :device-label="deviceLabel"
        :artifacts="artifacts"
        :events="eventsQuery.data.value"
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
        :can-reproduce="canReproduceFromSummary"
        @reproduce="handleReproduce"
      />
    </AppCard>
  </section>
</template>

<style scoped>
.page {
  display: grid;
  gap: 16px;
}

.page-padded {
  padding: 24px;
  max-width: 1120px;
  margin: 0 auto;
  width: 100%;
}

.header-row,
.header-main,
.actions,
.badge-row {
  display: grid;
  gap: 12px;
}

.header-row {
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: start;
}

.actions {
  grid-auto-flow: column;
  align-items: start;
}

.badge-row {
  display: flex;
  flex-wrap: wrap;
}

.secondary-button,
.danger-button {
  min-height: 38px;
  padding: 0 14px;
  border-radius: 8px;
  font: inherit;
}

.secondary-button {
  border: 1px solid var(--border-default);
  background: var(--surface-default);
  color: var(--text-primary);
}

.danger-button {
  border: 1px solid var(--status-error-text);
  background: var(--status-error-bg);
  color: var(--status-error-text);
}

.muted {
  color: var(--text-secondary);
}

.error-text {
  color: var(--status-error-text);
}

.success-text {
  color: var(--status-success-text);
}

@media (max-width: 880px) {
  .header-row {
    grid-template-columns: 1fr;
  }

  .actions {
    grid-auto-flow: row;
  }
}
</style>
