<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import AppBadge from '@/shared/components/AppBadge.vue'
import AppEmptyState from '@/shared/components/AppEmptyState.vue'
import RunTimelinePanel from '@/features/runs/components/RunTimelinePanel.vue'
import {
  rawPayload,
  statusTone,
  verdictTone,
} from '@/features/runs/lib/runMappers'
import type {
  BatchRunAggregateData,
  OperationChildItemData,
  OperationDetailData,
  OperationEventsData,
} from '@/shared/api/operations'

type TimePresenter = {
  datetime: (value: string | null | undefined) => string | null
  tooltip: (value: string | null | undefined) => string | null
  relative: (value: string | null | undefined) => string
  absolute: (value: string | null | undefined) => string
}

const props = defineProps<{
  detail: OperationDetailData
  deviceLabel: string
  events: OperationEventsData | null | undefined
  time: TimePresenter
}>()

const { t } = useI18n()

const activeTab = ref<'summary' | 'timeline' | 'raw'>('summary')
const batchAggregate = computed<BatchRunAggregateData | null>(() => props.detail.aggregate ?? null)
const batchChildren = computed<OperationChildItemData[]>(() => props.detail.children_preview ?? [])
const isPlanCaseBatchRun = computed(() => props.detail.batch_kind === 'single_plan_multi_case')
const batchPresentation = computed(() => {
  if (isPlanCaseBatchRun.value) {
    return {
      summaryTitle: t('runDetail.batch.caseBatch.summaryTitle'),
      summaryDescription: t('runDetail.batch.caseBatch.summaryDescription'),
      childRunsTitle: t('runDetail.batch.caseBatch.childRunsTitle'),
      childRunsDescription: t('runDetail.batch.caseBatch.childRunsDescription'),
      totalChildren: t('runDetail.batch.caseBatch.fields.totalChildren'),
      currentChild: t('runDetail.batch.caseBatch.fields.currentChild'),
      childLabel: t('runDetail.batch.caseBatch.fields.childLabel'),
    }
  }
  return {
    summaryTitle: t('runDetail.batch.planBatch.summaryTitle'),
    summaryDescription: t('runDetail.batch.planBatch.summaryDescription'),
    childRunsTitle: t('runDetail.batch.planBatch.childRunsTitle'),
    childRunsDescription: t('runDetail.batch.planBatch.childRunsDescription'),
    totalChildren: t('runDetail.batch.planBatch.fields.totalChildren'),
    currentChild: t('runDetail.batch.planBatch.fields.currentChild'),
    childLabel: t('runDetail.batch.planBatch.fields.childLabel'),
  }
})
const aggregateTokenUsage = computed(() => batchAggregate.value?.token_usage ?? null)

function formatTokenCount(value: number | null | undefined): string {
  return value == null ? '-' : new Intl.NumberFormat().format(value)
}

function batchChildIdentity(item: OperationChildItemData) {
  if (isPlanCaseBatchRun.value) {
    const caseId = (item as Record<string, unknown>).case_id
    return (typeof caseId === 'string' && caseId.length > 0 ? caseId : null) || item.operation_id
  }
  return item.plan_id || item.operation_id
}

function currentChildIdentity() {
  const aggregate = batchAggregate.value as Record<string, unknown> | null
  if (isPlanCaseBatchRun.value) {
    const caseId = aggregate?.current_child_case_id
    if (typeof caseId === 'string' && caseId.length > 0) {
      return caseId
    }
  }
  const planId = aggregate?.current_child_plan_id
  if (typeof planId === 'string' && planId.length > 0) {
    return planId
  }
  return '-'
}
</script>

<template>
  <div class="tab-row">
    <button type="button" class="tab-button" :class="{ active: activeTab === 'summary' }" @click="activeTab = 'summary'">
      {{ t('runDetail.tabs.summary') }}
    </button>
    <button type="button" class="tab-button" :class="{ active: activeTab === 'timeline' }" @click="activeTab = 'timeline'">
      {{ t('runDetail.tabs.timeline') }}
    </button>
    <button type="button" class="tab-button" :class="{ active: activeTab === 'raw' }" @click="activeTab = 'raw'">
      {{ t('runDetail.tabs.raw') }}
    </button>
  </div>

  <div v-if="activeTab === 'summary'" class="grid gap-4">
    <div class="grid gap-1">
      <h3 class="text-base font-semibold text-text-primary">{{ batchPresentation.summaryTitle }}</h3>
      <p class="text-sm text-text-secondary">{{ batchPresentation.summaryDescription }}</p>
    </div>
      <div class="grid gap-1">
        <h3 class="text-base font-semibold text-text-primary">{{ t('runDetail.batch.contextTitle') }}</h3>
        <p class="text-sm text-text-secondary">{{ t('runDetail.batch.contextDescription') }}</p>
      </div>
      <dl class="grid gap-3 md:grid-cols-3">
        <div class="grid gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
          <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('runs.fields.app') }}</dt>
          <dd class="break-all text-sm text-text-primary">{{ detail.app_id || '-' }}</dd>
        </div>
        <div class="grid gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
          <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('runs.fields.plan') }}</dt>
          <dd class="break-all text-sm text-text-primary">{{ detail.plan_id || '-' }}</dd>
        </div>
        <div class="grid gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
          <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('runs.fields.device') }}</dt>
          <dd class="break-all text-sm text-text-primary">{{ deviceLabel }}</dd>
        </div>
        <div class="grid gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
          <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('runs.fields.platform') }}</dt>
          <dd class="text-sm text-text-primary">{{ detail.platform || '-' }}</dd>
        </div>
        <div class="grid gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
          <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('runs.fields.createdAt') }}</dt>
          <dd class="text-sm text-text-primary">
            <time :datetime="time.datetime(detail.created_at) ?? undefined" :title="time.tooltip(detail.created_at) ?? undefined">
              {{ time.absolute(detail.created_at) }}
            </time>
          </dd>
        </div>
        <div class="grid gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
          <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('runDetail.fields.startedAt') }}</dt>
          <dd class="text-sm text-text-primary">
            <time :datetime="time.datetime(detail.started_at) ?? undefined" :title="time.tooltip(detail.started_at) ?? undefined">
              {{ time.absolute(detail.started_at) }}
            </time>
          </dd>
        </div>
      </dl>
    <dl class="grid gap-3 md:grid-cols-3">
      <div class="grid gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
        <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ batchPresentation.totalChildren }}</dt>
        <dd class="text-sm text-text-primary">{{ batchAggregate?.total_children ?? 0 }}</dd>
      </div>
      <div class="grid gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
        <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('runDetail.batch.fields.completedChildren') }}</dt>
        <dd class="text-sm text-text-primary">{{ batchAggregate?.completed_children ?? 0 }}</dd>
      </div>
      <div class="grid gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
        <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('runDetail.batch.fields.failedChildren') }}</dt>
        <dd class="text-sm text-text-primary">{{ batchAggregate?.failed_children ?? 0 }}</dd>
      </div>
      <div class="grid gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
        <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('runDetail.batch.fields.queuedChildren') }}</dt>
        <dd class="text-sm text-text-primary">{{ batchAggregate?.queued_children ?? 0 }}</dd>
      </div>
      <div class="grid gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
        <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('runDetail.batch.fields.runningChildren') }}</dt>
        <dd class="text-sm text-text-primary">{{ batchAggregate?.running_children ?? 0 }}</dd>
      </div>
      <div class="grid gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
        <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ batchPresentation.currentChild }}</dt>
        <dd class="break-all text-sm text-text-primary">
          {{ batchAggregate?.current_child_title || currentChildIdentity() }}
        </dd>
      </div>
      <div v-if="aggregateTokenUsage" class="grid gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
        <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('runDetail.usage.kinds.total') }}</dt>
        <dd class="text-sm text-text-primary">{{ formatTokenCount(aggregateTokenUsage.total_tokens) }}</dd>
      </div>
    </dl>

    <div class="grid gap-1">
      <h3 class="text-base font-semibold text-text-primary">{{ batchPresentation.childRunsTitle }}</h3>
      <p class="text-sm text-text-secondary">{{ batchPresentation.childRunsDescription }}</p>
    </div>
    <AppEmptyState
      v-if="batchChildren.length === 0"
      :title="batchPresentation.childRunsTitle"
      :description="t('runDetail.batch.emptyChildren')"
    />
    <div v-else class="grid gap-3">
      <article
        v-for="item in batchChildren"
        :key="item.operation_id"
        class="grid gap-3 rounded-xl border border-border-muted bg-surface-muted p-4 md:grid-cols-[minmax(0,1fr)_auto] md:items-start"
      >
        <div class="min-w-0 grid gap-2">
          <div class="flex flex-wrap items-center gap-2">
            <AppBadge>{{ item.position_label || item.position_index }}</AppBadge>
            <AppBadge :tone="statusTone(item.status)">{{ t(`runs.status.${item.status}`) }}</AppBadge>
            <AppBadge v-if="item.verification_verdict" :tone="verdictTone(item.verification_verdict)">
              {{ t(`runs.verdict.${item.verification_verdict}`) }}
            </AppBadge>
          </div>
          <strong class="break-words text-base text-text-primary">{{ item.title || batchChildIdentity(item) }}</strong>
          <div class="flex flex-wrap gap-x-3 gap-y-2 text-sm text-text-secondary">
            <span>{{ batchPresentation.childLabel }}: {{ batchChildIdentity(item) }}</span>
            <span>{{ item.operation_id }}</span>
            <span v-if="item.token_usage">{{ t('runDetail.usage.kinds.total') }}: {{ formatTokenCount(item.token_usage.total_tokens) }}</span>
          </div>
        </div>
        <div class="flex items-center gap-2 md:justify-self-end">
          <a class="secondary-link" :href="`/runs/${encodeURIComponent(item.operation_id)}`">
            {{ t('runDetail.batch.openChild') }}
          </a>
        </div>
      </article>
    </div>
  </div>

  <RunTimelinePanel
    v-else-if="activeTab === 'timeline'"
    :items="events?.items ?? []"
    :time="time"
  />

  <div v-else class="raw-panel">
    <pre>{{ rawPayload(detail) }}</pre>
  </div>
</template>

<style scoped>
.tab-row,
.raw-panel {
  display: grid;
  gap: 12px;
}

.tab-row {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.tab-button,
.secondary-link {
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

.secondary-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
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
}
</style>
