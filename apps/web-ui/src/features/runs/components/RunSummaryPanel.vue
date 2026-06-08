<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import AppBadge from '@/shared/components/AppBadge.vue'
import {
  sceneTokenUsages,
  type RunOrchestrationSummaryView,
  type TokenUsageView,
} from '@/features/runs/lib/runMappers'
import type { OperationDetailData } from '@/shared/api/operations'
import { verdictTone } from '@/features/runs/lib/runMappers'

type TimePresenter = {
  duration: (value: number | null | undefined) => string
  datetime: (value: string | null | undefined) => string | null
  tooltip: (value: string | null | undefined) => string | null
  absolute: (value: string | null | undefined) => string
}

type PlanRunProgressView = {
  totalCases: number
  completedCases: number
  currentCaseId: string | null
  lastCaseId: string | null
  percent: number | null
}

const props = defineProps<{
  detail: OperationDetailData
  deviceLabel: string
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
  (event: 'open-evidence', evidenceId: string): void
  (event: 'reproduce'): void
}>()

const { t } = useI18n()

const progressSummary = computed(() => props.progressSummary)
const orchestrationSummary = computed(() => props.orchestrationSummary)
const displayVerdict = computed(() => props.resultVerdict || props.detail.verification_verdict || null)
const conclusionTitle = computed(() => props.failureHypothesis || props.judgeReason || props.resultSummary || t('runDetail.summary.noConclusion'))
const hasSupplementalReason = computed(() => (
  Boolean(props.failureHypothesis && props.judgeReason && props.failureHypothesis !== props.judgeReason)
))
const summaryStatus = computed(() => {
  if (displayVerdict.value) {
    return t(`runs.verdict.${displayVerdict.value}`)
  }
  return t(`runs.status.${props.detail.status}`)
})
const orchestrationDecisionLabel = computed(() => {
  const decisionType = orchestrationSummary.value?.finalDecisionType
  if (!decisionType) {
    return null
  }
  if (decisionType === 'finish' || decisionType === 'retry_with_context' || decisionType === 'escalate') {
    return t(`runDetail.summary.orchestration.decisionTypes.${decisionType}`)
  }
  return decisionType
})
const orchestrationHeadline = computed(() => {
  const summary = orchestrationSummary.value
  if (!summary) {
    return null
  }
  if (summary.retried) {
    return t('runDetail.summary.orchestration.retriedHeadline', { count: summary.attemptCount })
  }
  return t('runDetail.summary.orchestration.singleAttemptHeadline')
})
const orchestrationSupplementalContext = computed(() => (
  orchestrationSummary.value?.supplementalContext ?? []
))
const usageSummary = computed(() => sceneTokenUsages(props.detail))
const usageCards = computed<Array<{ key: string, label: string, usage: TokenUsageView }>>(() => {
  const cards: Array<{ key: string, label: string, usage: TokenUsageView }> = []
  if (usageSummary.value.total) {
    cards.push({ key: 'total', label: tokenUsageLabel('total'), usage: usageSummary.value.total })
  }
  if (usageSummary.value.planning) {
    cards.push({ key: 'planning', label: tokenUsageLabel('planning'), usage: usageSummary.value.planning })
  }
  if (usageSummary.value.execution) {
    cards.push({ key: 'execution', label: tokenUsageLabel('execution'), usage: usageSummary.value.execution })
  }
  return cards
})
const hasTokenUsage = computed(() => (
  Boolean(usageSummary.value.total || usageSummary.value.planning || usageSummary.value.execution)
  || usageSummary.value.attempts.some((item) => item.runnerUsage || item.judgeUsage || item.totalUsage)
))

function formatTokenCount(value: number | null | undefined): string {
  return value == null ? '-' : new Intl.NumberFormat().format(value)
}

function tokenUsageHeadline(): string {
  if (props.detail.run_type === 'verify_change') {
    return t('runDetail.usage.headlines.verifyChange')
  }
  if (props.detail.run_type === 'plan_run' || props.detail.run_type === 'plan_batch_run') {
    return t('runDetail.usage.headlines.planExecution')
  }
  if (props.detail.run_type === 'case_run') {
    return t('runDetail.usage.headlines.caseRun')
  }
  return t('runDetail.usage.headlines.generic')
}

function tokenUsageLabel(kind: 'total' | 'planning' | 'execution') {
  return t(`runDetail.usage.kinds.${kind}`)
}

function handleOpenEvidence() {
  if (!props.primaryEvidenceId) {
    return
  }
  emit('open-evidence', props.primaryEvidenceId)
}
</script>

<template>
  <div class="summary-layout">
    <section class="summary-card">
      <div class="card-head">
        <span class="section-label">{{ t('runDetail.summary.conclusionTitle') }}</span>
        <AppBadge v-if="displayVerdict" :tone="verdictTone(displayVerdict)">
          {{ t(`runs.verdict.${displayVerdict}`) }}
        </AppBadge>
      </div>
      <strong class="conclusion-title">{{ conclusionTitle }}</strong>
      <p class="summary-status">{{ summaryStatus }}</p>
      <p v-if="hasSupplementalReason" class="supporting-text">{{ judgeReason }}</p>
      <p v-if="resultSummary && resultSummary !== conclusionTitle" class="supporting-text">{{ resultSummary }}</p>
    </section>

    <section class="summary-card">
      <div class="card-head">
        <span class="section-label">{{ t('runDetail.summary.actionsTitle') }}</span>
      </div>
      <div class="action-row">
        <button
          v-if="primaryEvidenceId"
          type="button"
          class="secondary-button"
          @click="handleOpenEvidence"
        >
          {{ t('runDetail.summary.openPrimaryEvidence') }}
        </button>
        <button
          v-if="canReproduce"
          type="button"
          class="secondary-button"
          @click="emit('reproduce')"
        >
          {{ t('runDetail.actions.reproduce') }}
        </button>
      </div>
      <div class="suggestion-list">
        <span class="meta-label">{{ t('runDetail.summary.nextStepsTitle') }}</span>
        <ul class="suggestions">
          <li v-for="suggestion in nextStepSuggestions" :key="suggestion">{{ suggestion }}</li>
        </ul>
      </div>
    </section>

    <section v-if="orchestrationSummary" class="summary-card">
      <div class="card-head">
        <span class="section-label">{{ t('runDetail.summary.orchestration.title') }}</span>
        <AppBadge :tone="orchestrationSummary.retried ? 'warning' : 'neutral'">
          {{ orchestrationSummary.attemptCount }}
          {{ t('runDetail.summary.orchestration.attemptsLabel') }}
        </AppBadge>
      </div>
      <strong class="conclusion-title">{{ orchestrationHeadline }}</strong>
      <p v-if="orchestrationSummary.finalDecisionSummary" class="supporting-text">
        {{ orchestrationSummary.finalDecisionSummary }}
      </p>
      <div class="panel-grid">
        <div class="meta-item">
          <span class="meta-label">{{ t('runDetail.summary.orchestration.fields.finalDecision') }}</span>
          <strong>{{ orchestrationDecisionLabel || '-' }}</strong>
        </div>
        <div class="meta-item">
          <span class="meta-label">{{ t('runDetail.summary.orchestration.fields.attemptCount') }}</span>
          <strong>{{ orchestrationSummary.attemptCount }}</strong>
        </div>
        <div class="meta-item full">
          <span class="meta-label">{{ t('runDetail.summary.orchestration.fields.decisionReason') }}</span>
          <strong>{{ orchestrationSummary.finalDecisionReason || '-' }}</strong>
        </div>
        <div class="meta-item full">
          <span class="meta-label">{{ t('runDetail.summary.orchestration.fields.latestRetryReason') }}</span>
          <strong>{{ orchestrationSummary.latestRetryReason || '-' }}</strong>
        </div>
        <div class="meta-item full">
          <span class="meta-label">{{ t('runDetail.summary.orchestration.fields.supplementalContext') }}</span>
          <strong>
            {{ orchestrationSupplementalContext.length > 0 ? orchestrationSupplementalContext.join(' | ') : '-' }}
          </strong>
        </div>
      </div>
    </section>

    <section v-if="hasTokenUsage" class="summary-card">
      <div class="card-head">
        <span class="section-label">{{ t('runDetail.usage.title') }}</span>
      </div>
      <strong class="conclusion-title">{{ tokenUsageHeadline() }}</strong>
      <div class="panel-grid">
        <article v-for="card in usageCards" :key="card.key" class="usage-card">
          <div class="usage-card-grid">
            <div class="meta-item">
              <span class="meta-label">{{ card.label }}</span>
              <strong>{{ formatTokenCount(card.usage.totalTokens) }}</strong>
            </div>
            <div class="meta-item">
              <span class="meta-label">{{ t('runDetail.usage.fields.inputTokens') }}</span>
              <strong>{{ formatTokenCount(card.usage.inputTokens) }}</strong>
            </div>
            <div class="meta-item">
              <span class="meta-label">{{ t('runDetail.usage.fields.outputTokens') }}</span>
              <strong>{{ formatTokenCount(card.usage.outputTokens) }}</strong>
            </div>
            <div class="meta-item">
              <span class="meta-label">{{ t('runDetail.usage.fields.cachedInputTokens') }}</span>
              <strong>{{ formatTokenCount(card.usage.cachedInputTokens) }}</strong>
            </div>
            <div class="meta-item">
              <span class="meta-label">{{ t('runDetail.usage.fields.reasoningTokens') }}</span>
              <strong>{{ formatTokenCount(card.usage.reasoningTokens) }}</strong>
            </div>
            <div class="meta-item">
              <span class="meta-label">{{ t('runDetail.usage.fields.requestCount') }}</span>
              <strong>{{ formatTokenCount(card.usage.requestCount) }}</strong>
            </div>
            <div class="meta-item full">
              <span class="meta-label">{{ t('runDetail.usage.fields.model') }}</span>
              <strong>{{ [card.usage.provider, card.usage.model].filter(Boolean).join(' / ') || '-' }}</strong>
            </div>
          </div>
        </article>
        <div v-if="props.detail.run_type === 'case_run' && usageSummary.attempts.length > 0" class="meta-item full">
          <span class="meta-label">{{ t('runDetail.usage.attemptsTitle') }}</span>
          <div class="attempt-usage-list">
            <article v-for="attempt in usageSummary.attempts" :key="attempt.attemptIndex" class="attempt-usage-item">
              <strong>{{ t('runDetail.usage.attemptLabel', { attempt: attempt.attemptIndex + 1 }) }}</strong>
              <div class="attempt-usage-grid">
                <div class="meta-item">
                  <span class="meta-label">{{ t('runDetail.usage.kinds.runner') }}</span>
                  <strong>{{ formatTokenCount(attempt.runnerUsage?.totalTokens) }}</strong>
                </div>
                <div class="meta-item">
                  <span class="meta-label">{{ t('runDetail.usage.kinds.judge') }}</span>
                  <strong>{{ formatTokenCount(attempt.judgeUsage?.totalTokens) }}</strong>
                </div>
                <div class="meta-item">
                  <span class="meta-label">{{ tokenUsageLabel('total') }}</span>
                  <strong>{{ formatTokenCount(attempt.totalUsage?.totalTokens) }}</strong>
                </div>
              </div>
            </article>
          </div>
        </div>
      </div>
    </section>

    <section class="details-card">
      <div class="card-head">
        <span class="section-label">{{ t('runDetail.summary.detailsTitle') }}</span>
      </div>
      <div class="panel-grid">
        <div class="meta-item"><span class="meta-label">{{ t('runs.fields.app') }}</span><strong>{{ detail.app_id || '-' }}</strong></div>
        <div class="meta-item"><span class="meta-label">{{ t('runs.fields.plan') }}</span><strong>{{ detail.plan_id || '-' }}</strong></div>
        <div class="meta-item"><span class="meta-label">{{ t('runs.fields.case') }}</span><strong>{{ detail.case_id || '-' }}</strong></div>
        <div class="meta-item"><span class="meta-label">{{ t('runs.fields.platform') }}</span><strong>{{ detail.platform || '-' }}</strong></div>
        <div class="meta-item"><span class="meta-label">{{ t('runs.fields.device') }}</span><strong>{{ deviceLabel }}</strong></div>
        <div class="meta-item"><span class="meta-label">{{ t('runs.fields.duration') }}</span><strong>{{ time.duration(detail.duration_ms) }}</strong></div>
        <div class="meta-item">
          <span class="meta-label">{{ t('runs.fields.createdAt') }}</span>
          <strong>
            <time :datetime="time.datetime(detail.created_at) ?? undefined" :title="time.tooltip(detail.created_at) ?? undefined">
              {{ time.absolute(detail.created_at) }}
            </time>
          </strong>
        </div>
        <div class="meta-item">
          <span class="meta-label">{{ t('runDetail.fields.startedAt') }}</span>
          <strong>
            <time :datetime="time.datetime(detail.started_at) ?? undefined" :title="time.tooltip(detail.started_at) ?? undefined">
              {{ time.absolute(detail.started_at) }}
            </time>
          </strong>
        </div>
        <div class="meta-item">
          <span class="meta-label">{{ t('runDetail.fields.finishedAt') }}</span>
          <strong>
            <time :datetime="time.datetime(detail.finished_at) ?? undefined" :title="time.tooltip(detail.finished_at) ?? undefined">
              {{ time.absolute(detail.finished_at) }}
            </time>
          </strong>
        </div>
        <div class="meta-item"><span class="meta-label">{{ t('runDetail.fields.errorCode') }}</span><strong>{{ detail.error_code || '-' }}</strong></div>
        <div class="meta-item full"><span class="meta-label">{{ t('runDetail.fields.errorMessage') }}</span><strong>{{ detail.error_message || '-' }}</strong></div>
        <div class="meta-item full"><span class="meta-label">{{ t('runDetail.fields.resultSummary') }}</span><strong>{{ resultSummary || '-' }}</strong></div>
        <div class="meta-item full"><span class="meta-label">{{ t('runDetail.fields.judgeReason') }}</span><strong>{{ judgeReason || '-' }}</strong></div>
        <div class="meta-item full"><span class="meta-label">{{ t('runDetail.fields.failureHypothesis') }}</span><strong>{{ failureHypothesis || '-' }}</strong></div>
        <div class="meta-item"><span class="meta-label">{{ t('runDetail.fields.confidence') }}</span><strong>{{ confidence == null ? '-' : confidence }}</strong></div>
        <div class="meta-item full">
          <span class="meta-label">{{ t('runDetail.fields.missingEvidence') }}</span>
          <strong>{{ missingEvidence.length > 0 ? missingEvidence.join(', ') : '-' }}</strong>
        </div>
        <template v-if="progressSummary">
          <div class="meta-item full">
            <span class="meta-label">{{ t('runDetail.progressTitle') }}</span>
            <strong>{{ t('runDetail.progressDescription') }}</strong>
          </div>
          <div class="meta-item"><span class="meta-label">{{ t('runDetail.fields.totalCases') }}</span><strong>{{ progressSummary.totalCases }}</strong></div>
          <div class="meta-item"><span class="meta-label">{{ t('runDetail.fields.completedCases') }}</span><strong>{{ progressSummary.completedCases }}</strong></div>
          <div class="meta-item"><span class="meta-label">{{ t('runDetail.fields.currentCaseId') }}</span><strong>{{ progressSummary.currentCaseId || '-' }}</strong></div>
          <div class="meta-item"><span class="meta-label">{{ t('runDetail.fields.lastCaseId') }}</span><strong>{{ progressSummary.lastCaseId || '-' }}</strong></div>
          <div class="meta-item"><span class="meta-label">{{ t('runDetail.fields.progressPercent') }}</span><strong>{{ progressSummary.percent == null ? '-' : `${progressSummary.percent}%` }}</strong></div>
        </template>
      </div>
    </section>
  </div>
</template>

<style scoped>
.summary-layout,
.summary-card,
.details-card,
.card-head,
.suggestion-list {
  display: grid;
  gap: 12px;
}

.summary-layout {
  gap: 16px;
}

.summary-card,
.details-card {
  padding: 16px;
  border-radius: 12px;
  border: 1px solid var(--border-muted);
  background: var(--surface-subtle);
}

.card-head {
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: start;
}

.section-label,
.panel-grid {
  min-width: 0;
}

.section-label,
.meta-label,
.summary-status,
.supporting-text {
  color: var(--text-secondary);
}

.section-label {
  font-size: 0.82rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.conclusion-title {
  font-size: 1.05rem;
  line-height: 1.5;
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.secondary-button {
  min-height: 38px;
  padding: 0 14px;
  border-radius: 8px;
  font: inherit;
  border: 1px solid var(--border-default);
  background: var(--surface-default);
  color: var(--text-primary);
}

.suggestions {
  margin: 0;
  padding-left: 18px;
  display: grid;
  gap: 8px;
}

.panel-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.attempt-usage-list,
.attempt-usage-item,
.attempt-usage-grid,
.usage-card,
.usage-card-grid {
  display: grid;
  gap: 12px;
}

.usage-card {
  grid-column: 1 / -1;
  padding: 12px;
  border-radius: 10px;
  border: 1px solid var(--border-muted);
  background: var(--surface-default);
}

.usage-card-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.attempt-usage-item {
  padding: 12px;
  border-radius: 10px;
  border: 1px solid var(--border-muted);
  background: var(--surface-default);
}

.attempt-usage-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.meta-item {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.meta-item.full {
  grid-column: 1 / -1;
}

.meta-item strong,
.conclusion-title,
.supporting-text {
  min-width: 0;
  overflow-wrap: anywhere;
}

@media (max-width: 880px) {
  .panel-grid {
    grid-template-columns: 1fr;
  }

  .attempt-usage-grid {
    grid-template-columns: 1fr;
  }

  .usage-card-grid {
    grid-template-columns: 1fr;
  }
}
</style>
