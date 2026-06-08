<script setup lang="ts">
import { Activity, Boxes, RefreshCcw, Smartphone, TestTube2 } from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import AppBadge from '@/shared/components/AppBadge.vue'
import AppEmptyState from '@/shared/components/AppEmptyState.vue'
import AppStatCard from '@/shared/components/AppStatCard.vue'
import { LocalApiClientError } from '@/shared/api/client'
import { translateErrorCode } from '@/shared/i18n/errorMessages'
import { useTime } from '@/shared/time/useTime'
import { formatDeviceLabel } from '@/features/devices/deviceLabels'
import { useDevicesQuery } from '@/features/devices/queries/useDevicesQuery'
import { useDashboardSummaryQuery } from '@/features/home/queries/useDashboardSummaryQuery'
import { useRecentRunsQuery } from '@/features/home/queries/useRecentRunsQuery'
import { displayRunListContext, displayRunTitle } from '@/features/runs/lib/runMappers'

const { t } = useI18n()
const time = useTime({ relative: true })

const summaryQuery = useDashboardSummaryQuery()
const recentRunsQuery = useRecentRunsQuery()
const devicesQuery = useDevicesQuery('all')

const summary = computed(() => summaryQuery.data.value)
const recentRuns = computed(() => recentRunsQuery.data.value ?? [])
const statsErrorMessage = computed(() => {
  const error = summaryQuery.error.value ?? devicesQuery.error.value
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
const recentRunsErrorMessage = computed(() => {
  const error = recentRunsQuery.error.value
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
const recentRunsLoading = computed(() => recentRunsQuery.isFetching.value && recentRuns.value.length === 0)
const connectedDeviceCount = computed(() => {
  const devices = devicesQuery.data.value
  if (devices) {
    return devices.filter((device) => device.availability === 'available').length
  }
  if (devicesQuery.isFetching.value) {
    return t('common.loading')
  }
  return '-'
})
const planCountValue = computed(() => {
  if (summary.value) {
    return summary.value.plan_count
  }
  return summaryQuery.isFetching.value ? t('common.loading') : '-'
})
const caseCountValue = computed(() => {
  if (summary.value) {
    return summary.value.case_count
  }
  return summaryQuery.isFetching.value ? t('common.loading') : '-'
})
const recentRunCountValue = computed(() => {
  if (summary.value) {
    return summary.value.recent_run_count
  }
  return summaryQuery.isFetching.value ? t('common.loading') : '-'
})

function toneForStatus(status: string): 'neutral' | 'success' | 'error' | 'warning' {
  if (status === 'succeeded') {
    return 'success'
  }
  if (status === 'failed' || status === 'cancelled') {
    return 'error'
  }
  if (status === 'running') {
    return 'warning'
  }
  return 'neutral'
}

function deviceLabel(deviceRef: string | null | undefined): string {
  return formatDeviceLabel(deviceRef, devicesQuery.data.value ?? [], t('home.unassignedDevice'))
}

</script>

<template>
  <section class="app-page">
    <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <AppStatCard :label="t('home.stats.plans')" :value="planCountValue" :icon="Boxes" />
      <AppStatCard :label="t('home.stats.cases')" :value="caseCountValue" :icon="TestTube2" />
      <AppStatCard :label="t('home.stats.recentRuns')" :value="recentRunCountValue" :icon="Activity" />
      <AppStatCard :label="t('home.stats.connectedDevices')" :value="connectedDeviceCount" :icon="Smartphone" />
    </div>
    <p v-if="statsErrorMessage" class="text-sm text-text-secondary">{{ statsErrorMessage }}</p>

    <div class="grid gap-4 xl:grid-cols-[minmax(0,1.75fr)_minmax(320px,1fr)]">
      <div class="grid gap-4">
        <div class="flex items-start justify-between gap-3">
          <div class="grid gap-1">
            <h2 class="app-section-title">{{ t('home.recentActivity.title') }}</h2>
          </div>
          <button type="button" class="inline-flex min-h-9 items-center gap-2 rounded-md border border-border bg-surface-default px-3 text-sm font-medium text-text-primary transition-colors hover:border-border-strong hover:bg-surface-muted" @click="() => { void summaryQuery.refetch(); void recentRunsQuery.refetch(); void devicesQuery.refetch() }">
            <RefreshCcw class="h-4 w-4 text-text-secondary" />
            {{ t('common.refresh') }}
          </button>
        </div>
        <p v-if="recentRunsLoading" class="text-sm text-text-secondary">{{ t('common.loading') }}</p>
        <AppEmptyState
          v-else-if="recentRunsErrorMessage"
          :title="t('home.recentActivity.errorTitle')"
          :description="recentRunsErrorMessage"
        />
        <AppEmptyState
          v-else-if="recentRuns.length === 0"
          :title="t('home.recentActivity.emptyTitle')"
          :description="t('home.recentActivity.emptyDescription')"
        />
        <div v-else class="grid gap-3">
          <article v-for="item in recentRuns" :key="item.operation_id" class="grid gap-2 rounded-lg border border-border-muted bg-surface-default p-3">
            <div class="grid gap-2">
              <div class="flex items-start justify-between gap-3">
                <RouterLink class="text-sm font-semibold text-text-primary transition-colors hover:text-accent" :to="`/runs/${encodeURIComponent(item.operation_id)}`">
                  {{ displayRunTitle(item) }}
                </RouterLink>
                <AppBadge :tone="toneForStatus(item.status)">{{ item.status }}</AppBadge>
              </div>
              <div class="flex flex-wrap gap-x-3 gap-y-2 text-sm text-text-secondary">
                <span>{{ item.run_type || item.kind }}</span>
                <span>{{ displayRunListContext(item) }}</span>
                <span>{{ deviceLabel(item.device_ref) }}</span>
                <time
                  :datetime="time.datetime(item.created_at) ?? undefined"
                  :title="time.tooltip(item.created_at)"
                >
                  {{ time.relative(item.created_at) }}
                </time>
              </div>
            </div>
          </article>
        </div>
      </div>

      <div class="grid content-start gap-4">
        <div class="grid gap-2">
          <h2 class="app-section-title">{{ t('home.quickActions.title') }}</h2>
          <p class="app-section-description">{{ t('home.quickActions.description') }}</p>
        </div>
        <div class="grid gap-3">
          <RouterLink class="flex min-h-10 items-center justify-between rounded-lg border border-border bg-surface-default px-3 text-sm font-medium text-text-primary transition-colors hover:border-border-strong hover:bg-surface-muted" to="/recording">
            <span>{{ t('home.quickActions.recording') }}</span>
          </RouterLink>
          <RouterLink class="flex min-h-10 items-center justify-between rounded-lg border border-border bg-surface-default px-3 text-sm font-medium text-text-primary transition-colors hover:border-border-strong hover:bg-surface-muted" to="/tests">
            <span>{{ t('home.quickActions.tests') }}</span>
          </RouterLink>
          <RouterLink class="flex min-h-10 items-center justify-between rounded-lg border border-border bg-surface-default px-3 text-sm font-medium text-text-primary transition-colors hover:border-border-strong hover:bg-surface-muted" to="/runs">
            <span>{{ t('home.quickActions.runs') }}</span>
          </RouterLink>
          <RouterLink class="flex min-h-10 items-center justify-between rounded-lg border border-border bg-surface-default px-3 text-sm font-medium text-text-primary transition-colors hover:border-border-strong hover:bg-surface-muted" to="/schedules">
            <span>{{ t('home.quickActions.schedules') }}</span>
          </RouterLink>
        </div>
      </div>
    </div>
  </section>
</template>
