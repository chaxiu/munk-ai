<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import AppBadge from '@/shared/components/AppBadge.vue'
import AppCard from '@/shared/components/AppCard.vue'
import AppEmptyState from '@/shared/components/AppEmptyState.vue'
import { LocalApiClientError } from '@/shared/api/client'
import { translateErrorCode } from '@/shared/i18n/errorMessages'
import { useTime } from '@/shared/time/useTime'
import { usePlanCreationProgress } from '@/features/tests/queries/usePlanCreationProgress'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const time = useTime({ relative: true })

const operationId = computed(() => String(route.params.operationId))
const progress = usePlanCreationProgress(operationId)

const operation = computed(() => progress.operation.value)
const progressStage = computed(() => String(operation.value?.progress?.stage ?? operation.value?.progress?.plan_event_type ?? t('testsCreate.progress.stageUnknown')))
const resultData = computed<Record<string, unknown> | null>(() => {
  const raw = operation.value?.result
  return raw && typeof raw === 'object' ? raw as Record<string, unknown> : null
})
const planResult = computed<Record<string, unknown> | null>(() => {
  const raw = resultData.value?.plan_result
  return raw && typeof raw === 'object' ? raw as Record<string, unknown> : null
})
const effectiveAppId = computed(() => {
  const resultAppId = resultData.value?.app_id
  if (typeof resultAppId === 'string' && resultAppId) {
    return resultAppId
  }
  return operation.value?.app_id ?? null
})
const effectivePlanId = computed(() => {
  const resultPlanId = resultData.value?.plan_id
  if (typeof resultPlanId === 'string' && resultPlanId) {
    return resultPlanId
  }
  return operation.value?.plan_id ?? null
})
const effectivePlanName = computed(() => {
  const resultPlanName = resultData.value?.plan_name
  if (typeof resultPlanName === 'string' && resultPlanName.trim()) {
    return resultPlanName
  }
  const nestedPlanName = planResult.value?.plan_name
  if (typeof nestedPlanName === 'string' && nestedPlanName.trim()) {
    return nestedPlanName
  }
  const progressPlanName = operation.value?.progress?.plan_name
  if (typeof progressPlanName === 'string' && progressPlanName.trim()) {
    return progressPlanName
  }
  return effectivePlanId.value
})
const latestCaseTitle = computed(() => {
  const progressCaseTitle = operation.value?.progress?.case_title
  if (typeof progressCaseTitle === 'string' && progressCaseTitle.trim()) {
    return progressCaseTitle
  }
  return null
})
const planningUsage = computed(() => operation.value?.planning_usage ?? null)
const executionUsage = computed(() => operation.value?.execution_usage ?? null)
const totalUsage = computed(() => operation.value?.token_usage ?? null)

function formatTokenCount(value: number | null | undefined): string {
  return value == null ? '-' : new Intl.NumberFormat().format(value)
}

const errorMessage = computed(() => {
  const error = progress.error.value
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

const canComplete = computed(() => (
  operation.value?.status === 'succeeded'
  && Boolean(effectiveAppId.value)
  && Boolean(effectivePlanId.value)
))

function statusTone(status?: string): 'neutral' | 'success' | 'error' | 'warning' {
  if (status === 'succeeded') {
    return 'success'
  }
  if (status === 'failed' || status === 'cancelled') {
    return 'error'
  }
  if (status === 'running' || status === 'queued') {
    return 'warning'
  }
  return 'neutral'
}

async function handleComplete() {
  if (!canComplete.value || !effectiveAppId.value || !effectivePlanId.value) {
    return
  }
  await router.push(`/tests/plans/${encodeURIComponent(effectiveAppId.value)}/${encodeURIComponent(effectivePlanId.value)}`)
}

async function backToTests() {
  await router.push('/tests')
}
</script>

<template>
  <section class="page page-padded">
    <AppCard>
      <div class="status-row">
        <div class="status-main">
          <strong>{{ operationId }}</strong>
          <AppBadge :tone="statusTone(operation?.status)">{{ operation?.status ?? t('common.loading') }}</AppBadge>
        </div>
        <button type="button" class="text-button" @click="progress.refetch">
          {{ t('common.refresh') }}
        </button>
      </div>

      <p v-if="progress.loading.value && !operation" class="muted">{{ t('common.loading') }}</p>
      <AppEmptyState
        v-else-if="errorMessage"
        :title="t('testsCreate.progress.errorTitle')"
        :description="errorMessage"
      />
      <template v-else-if="operation">
        <div class="meta-grid">
          <div class="meta-item">
            <span class="meta-label">{{ t('testsCreate.progress.fields.phase') }}</span>
            <strong>{{ resultData?.phase ?? t('recording.none') }}</strong>
          </div>
          <div class="meta-item">
            <span class="meta-label">{{ t('testsCreate.progress.fields.stage') }}</span>
            <strong>{{ progressStage }}</strong>
          </div>
          <div class="meta-item">
            <span class="meta-label">{{ t('testsCreate.progress.fields.planId') }}</span>
            <strong>{{ effectivePlanName ?? t('recording.none') }}</strong>
            <span class="muted">{{ effectivePlanId ?? t('recording.none') }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">{{ t('testsCreate.progress.fields.caseProgress') }}</span>
            <strong>
              {{ operation.progress?.completed_case_count ?? 0 }}/{{ operation.progress?.target_case_count ?? '-' }}
            </strong>
          </div>
          <div v-if="latestCaseTitle" class="meta-item">
            <span class="meta-label">{{ t('testsCreate.progress.fields.currentCase') }}</span>
            <strong>{{ latestCaseTitle }}</strong>
          </div>
        </div>

        <AppCard v-if="planningUsage || executionUsage || totalUsage">
          <div class="section-title-row">
            <h2>{{ t('runDetail.usage.title') }}</h2>
          </div>
          <div class="meta-grid">
            <div v-if="planningUsage" class="meta-item">
              <span class="meta-label">{{ t('runDetail.usage.kinds.planning') }}</span>
              <strong>{{ formatTokenCount(planningUsage.total_tokens) }}</strong>
            </div>
            <div v-if="executionUsage" class="meta-item">
              <span class="meta-label">{{ t('runDetail.usage.kinds.execution') }}</span>
              <strong>{{ formatTokenCount(executionUsage.total_tokens) }}</strong>
            </div>
            <div v-if="totalUsage" class="meta-item">
              <span class="meta-label">{{ t('runDetail.usage.kinds.total') }}</span>
              <strong>{{ formatTokenCount(totalUsage.total_tokens) }}</strong>
            </div>
          </div>
        </AppCard>

        <AppCard>
          <div class="section-title-row">
            <h2>{{ t('testsCreate.progress.eventsTitle') }}</h2>
          </div>
          <AppEmptyState
            v-if="progress.events.value.length === 0"
            :title="t('testsCreate.progress.emptyEventsTitle')"
            :description="t('testsCreate.progress.emptyEventsDescription')"
          />
          <div v-else class="event-list">
            <article v-for="item in progress.events.value" :key="item.seq" class="event-row">
              <div class="event-row-top">
                <strong>{{ item.message || item.event_type }}</strong>
                <span class="muted">#{{ item.seq }}</span>
              </div>
              <div class="event-meta">
                <span>{{ item.event_type }}</span>
                <time
                  :datetime="time.datetime(item.timestamp) ?? undefined"
                  :title="time.tooltip(item.timestamp)"
                >
                  {{ time.relative(item.timestamp) }}
                </time>
              </div>
            </article>
          </div>
        </AppCard>

        <AppCard v-if="canComplete && planResult">
          <div class="section-title-row">
            <h2>{{ t('testsCreate.progress.resultTitle') }}</h2>
          </div>
          <div class="meta-grid">
            <div class="meta-item">
              <span class="meta-label">{{ t('testsCreate.progress.fields.caseCount') }}</span>
              <strong>{{ planResult.case_count ?? '-' }}</strong>
            </div>
            <div class="meta-item">
              <span class="meta-label">{{ t('testsCreate.progress.fields.planPath') }}</span>
              <strong>{{ planResult.plan_path ?? '-' }}</strong>
            </div>
            <div class="meta-item">
              <span class="meta-label">{{ t('testsCreate.progress.fields.snapshotPath') }}</span>
              <strong>{{ planResult.snapshot_path ?? '-' }}</strong>
            </div>
          </div>
        </AppCard>

        <AppCard v-else-if="operation.status === 'failed' || operation.status === 'cancelled'">
          <div class="section-title-row">
            <h2>{{ t('testsCreate.progress.failedTitle') }}</h2>
          </div>
          <div class="meta-grid">
            <div class="meta-item">
              <span class="meta-label">{{ t('testsCreate.progress.fields.errorCode') }}</span>
              <strong>{{ operation.error_code ?? '-' }}</strong>
            </div>
            <div class="meta-item">
              <span class="meta-label">{{ t('testsCreate.progress.fields.errorMessage') }}</span>
              <strong>{{ operation.error_message ?? '-' }}</strong>
            </div>
          </div>
        </AppCard>
      </template>
    </AppCard>

    <div class="actions">
      <button type="button" class="secondary-button" @click="backToTests">
        {{ t('testsCreate.actions.backToTests') }}
      </button>
      <button type="button" class="primary-button" :disabled="!canComplete" @click="handleComplete">
        {{ t('testsCreate.actions.complete') }}
      </button>
    </div>
  </section>
</template>

<style scoped>
.page {
  display: grid;
  gap: 20px;
}

.page-padded {
  padding: 24px;
  max-width: 1120px;
  margin: 0 auto;
  width: 100%;
}

.status-row,
.status-main,
.section-title-row,
.actions {
  display: flex;
  gap: 12px;
}

.status-row,
.section-title-row,
.actions {
  align-items: center;
  justify-content: space-between;
}

.status-main {
  align-items: center;
}

.meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.meta-item {
  display: grid;
  gap: 6px;
}

.meta-label,
.muted,
.event-meta {
  color: var(--text-secondary);
}

.event-list {
  display: grid;
  gap: 12px;
}

.event-row {
  padding-top: 12px;
  border-top: 1px solid var(--border-muted);
}

.event-row-top,
.event-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.event-meta {
  flex-wrap: wrap;
  font-size: 0.92rem;
}

.text-button {
  border: 0;
  background: transparent;
  color: var(--accent-primary);
  cursor: pointer;
  font: inherit;
}

.primary-button,
.secondary-button {
  min-height: 40px;
  padding: 0 16px;
  border-radius: 8px;
  font: inherit;
  cursor: pointer;
}

.primary-button {
  border: 1px solid var(--accent-primary);
  background: var(--accent-primary);
  color: white;
}

.secondary-button {
  border: 1px solid var(--border-default);
  background: var(--surface-default);
  color: var(--text-primary);
}

.primary-button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

@media (max-width: 720px) {
  .status-row,
  .section-title-row,
  .actions,
  .event-row-top,
  .event-meta {
    display: grid;
    justify-content: stretch;
  }

  .meta-grid {
    grid-template-columns: 1fr;
  }
}
</style>
