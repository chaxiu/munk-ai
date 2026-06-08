<script setup lang="ts">
import { RefreshCcw, Search } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import AppBadge from '@/shared/components/AppBadge.vue'
import AppCard from '@/shared/components/AppCard.vue'
import AppEmptyState from '@/shared/components/AppEmptyState.vue'
import UiInput from '@/shared/ui/UiInput.vue'
import UiSelect from '@/shared/ui/UiSelect.vue'
import { formatDeviceLabel } from '@/features/devices/deviceLabels'
import { useDevicesQuery } from '@/features/devices/queries/useDevicesQuery'
import { LocalApiClientError } from '@/shared/api/client'
import { translateErrorCode } from '@/shared/i18n/errorMessages'
import { useTime } from '@/shared/time/useTime'
import { useRunsQuery } from '@/features/runs/queries/useRunsQuery'
import {
  describePhase,
  displayRunListContext,
  displayRunTitle,
  statusTone,
  verdictTone,
} from '@/features/runs/lib/runMappers'

const PAGE_SIZE = 20

const { t } = useI18n()
const time = useTime({ relative: true })

const runTypeFilter = ref('all')
const platformFilter = ref('all')
const statusFilter = ref('all')
const verdictFilter = ref('all')
const deviceFilter = ref('')
const queryFilter = ref('')
const page = ref(1)
const devicesQuery = useDevicesQuery('all')

const offset = computed(() => (page.value - 1) * PAGE_SIZE)

const runsQuery = useRunsQuery(computed(() => ({
  limit: PAGE_SIZE,
  offset: offset.value,
  runType: runTypeFilter.value === 'all' ? undefined : runTypeFilter.value,
  surface: 'run_center',
  status: statusFilter.value === 'all' ? undefined : statusFilter.value as 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled',
  deviceRef: deviceFilter.value.trim() || undefined,
  verificationVerdict: verdictFilter.value === 'all' ? undefined : verdictFilter.value,
  platform: platformFilter.value === 'all' ? undefined : platformFilter.value,
  query: queryFilter.value.trim() || undefined,
})))

const runs = computed(() => runsQuery.data.value?.items ?? [])
const total = computed(() => runsQuery.data.value?.total ?? 0)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))
const hasPreviousPage = computed(() => page.value > 1)
const hasNextPage = computed(() => page.value < totalPages.value)

watch([runTypeFilter, platformFilter, statusFilter, verdictFilter, deviceFilter, queryFilter], () => {
  page.value = 1
})

const errorMessage = computed(() => {
  const error = runsQuery.error.value
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

const runTypeOptions = computed(() => [
  { value: 'all', label: t('runs.filters.allTypes') },
  { value: 'case_run', label: t('runs.types.case_run') },
  { value: 'plan_run', label: t('runs.types.plan_run') },
  { value: 'plan_batch_run', label: t('runs.types.plan_batch_run') },
  { value: 'verify_change', label: t('runs.types.verify_change') },
  { value: 'replay', label: t('runs.types.replay') },
])

const platformOptions = computed(() => [
  { value: 'all', label: t('runs.filters.allPlatforms') },
  { value: 'android', label: 'Android' },
  { value: 'ios', label: 'iOS' },
  { value: 'web', label: 'Web' },
])

const statusOptions = computed(() => [
  { value: 'all', label: t('runs.filters.allStatuses') },
  { value: 'queued', label: t('runs.status.queued') },
  { value: 'running', label: t('runs.status.running') },
  { value: 'succeeded', label: t('runs.status.succeeded') },
  { value: 'failed', label: t('runs.status.failed') },
  { value: 'cancelled', label: t('runs.status.cancelled') },
])

const verdictOptions = computed(() => [
  { value: 'all', label: t('runs.filters.allVerdicts') },
  { value: 'passed', label: t('runs.verdict.passed') },
  { value: 'failed', label: t('runs.verdict.failed') },
  { value: 'inconclusive', label: t('runs.verdict.inconclusive') },
])

function goToPreviousPage() {
  if (hasPreviousPage.value) {
    page.value -= 1
  }
}

function goToNextPage() {
  if (hasNextPage.value) {
    page.value += 1
  }
}

function deviceLabel(deviceRef: string | null | undefined): string {
  return formatDeviceLabel(deviceRef, devicesQuery.data.value ?? [], t('recording.none'))
}
</script>

<template>
  <section class="app-page">
    <div class="grid gap-4">
      <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <UiSelect v-model="runTypeFilter" :options="runTypeOptions" :placeholder="t('runs.filters.allTypes')" />
        <UiSelect v-model="platformFilter" :options="platformOptions" :placeholder="t('runs.filters.allPlatforms')" />
        <UiSelect v-model="statusFilter" :options="statusOptions" :placeholder="t('runs.filters.allStatuses')" />
        <UiSelect v-model="verdictFilter" :options="verdictOptions" :placeholder="t('runs.filters.allVerdicts')" />
        <div class="relative">
          <Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
          <UiInput v-model="deviceFilter" :placeholder="t('runs.filters.devicePlaceholder')" class="pl-10" />
        </div>
        <div class="relative">
          <Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
          <UiInput v-model="queryFilter" :placeholder="t('runs.filters.queryPlaceholder')" class="pl-10" />
        </div>
      </div>
      <div class="flex justify-end">
        <button type="button" class="inline-flex min-h-9 items-center gap-2 rounded-md border border-border bg-surface-default px-3 text-sm font-medium text-text-primary transition-colors hover:border-border-strong hover:bg-surface-muted" @click="() => void runsQuery.refetch()">
          <RefreshCcw class="h-4 w-4 text-text-secondary" />
          {{ t('common.refresh') }}
        </button>
      </div>
    </div>

    <AppCard v-if="runsQuery.isFetching.value && runs.length === 0">
      <p class="text-sm text-text-secondary">{{ t('common.loading') }}</p>
    </AppCard>

    <AppEmptyState
      v-else-if="errorMessage"
      :title="t('runs.errorTitle')"
      :description="errorMessage"
    />

    <AppEmptyState
      v-else-if="runs.length === 0"
      :title="t('runs.emptyTitle')"
      :description="t('runs.emptyDescription')"
    />

    <div v-else class="grid gap-3">
      <article v-for="item in runs" :key="item.operation_id" class="grid gap-2 rounded-lg border border-border-muted bg-surface-default p-3">
        <div class="grid gap-2">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div class="flex flex-wrap items-center gap-2">
              <RouterLink class="text-sm font-semibold text-text-primary transition-colors hover:text-accent" :to="`/runs/${encodeURIComponent(item.operation_id)}`">
                {{ displayRunTitle(item) }}
              </RouterLink>
              <AppBadge :tone="statusTone(item.status)">{{ t(`runs.status.${item.status}`) }}</AppBadge>
              <AppBadge v-if="item.verification_verdict" :tone="verdictTone(item.verification_verdict)">
                {{ t(`runs.verdict.${item.verification_verdict}`) }}
              </AppBadge>
              <AppBadge v-if="describePhase(item) === 'planned'" tone="warning">
                {{ t('runs.phase.planned') }}
              </AppBadge>
            </div>
            <AppBadge>
              {{ item.run_type ? t(`runs.types.${item.run_type}`) : item.kind }}
            </AppBadge>
          </div>
          <p class="text-sm text-text-secondary">{{ displayRunListContext(item) }}</p>
          <div class="flex flex-wrap gap-x-3 gap-y-2 text-sm text-text-secondary">
            <span>{{ t('runs.fields.device') }}: {{ deviceLabel(item.device_ref) }}</span>
            <span>{{ t('runs.fields.platform') }}: {{ item.platform || '-' }}</span>
            <span>
              {{ t('runs.fields.createdAt') }}:
              <time
                :datetime="time.datetime(item.created_at) ?? undefined"
                :title="time.tooltip(item.created_at)"
              >
                {{ time.relative(item.created_at) }}
              </time>
            </span>
          </div>
        </div>
      </article>

      <div class="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border-muted bg-surface-default px-4 py-3">
        <span class="text-sm text-text-secondary">
          {{ t('runs.pagination.summary', { page, totalPages, total }) }}
        </span>
        <div class="flex items-center gap-2">
          <button
            type="button"
            class="inline-flex min-h-9 items-center rounded-md border border-border bg-surface-default px-3 text-sm font-medium text-text-primary transition-colors hover:border-border-strong hover:bg-surface-muted disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="!hasPreviousPage"
            @click="goToPreviousPage"
          >
            {{ t('runs.pagination.previous') }}
          </button>
          <button
            type="button"
            class="inline-flex min-h-9 items-center rounded-md border border-border bg-surface-default px-3 text-sm font-medium text-text-primary transition-colors hover:border-border-strong hover:bg-surface-muted disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="!hasNextPage"
            @click="goToNextPage"
          >
            {{ t('runs.pagination.next') }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>
