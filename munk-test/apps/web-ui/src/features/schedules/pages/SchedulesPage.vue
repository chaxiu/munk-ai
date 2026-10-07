<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import AppBadge from '@/shared/components/AppBadge.vue'
import AppCard from '@/shared/components/AppCard.vue'
import AppEmptyState from '@/shared/components/AppEmptyState.vue'
import { LocalApiClientError } from '@/shared/api/client'
import { translateErrorCode } from '@/shared/i18n/errorMessages'
import { useTime } from '@/shared/time/useTime'
import UiButton from '@/shared/ui/UiButton.vue'
import UiInput from '@/shared/ui/UiInput.vue'
import UiSelect from '@/shared/ui/UiSelect.vue'
import { useAppsQuery } from '@/features/apps/queries/useAppsQuery'
import { formatDeviceLabel } from '@/features/devices/deviceLabels'
import { useDevicesQuery } from '@/features/devices/queries/useDevicesQuery'
import { useScheduleMutations } from '../queries/useScheduleMutations'
import { useSchedulesQuery } from '../queries/useSchedulesQuery'

type ScheduleStatusFilter = 'all' | 'enabled' | 'disabled'

const ALL_APPS_FILTER = '__all_apps__'
const PAGE_SIZE = 20

const { t } = useI18n()
const time = useTime({ relative: true })
const statusFilter = ref<ScheduleStatusFilter>('all')
const selectedAppId = ref(ALL_APPS_FILTER)
const keyword = ref('')
const page = ref(1)
const scheduleFilters = computed(() => ({
  enabled: statusFilter.value === 'all'
    ? undefined
    : statusFilter.value === 'enabled',
  appId: selectedAppId.value === ALL_APPS_FILTER
    ? undefined
    : selectedAppId.value.trim() || undefined,
  keyword: keyword.value.trim() || undefined,
  limit: PAGE_SIZE,
  offset: (page.value - 1) * PAGE_SIZE,
}))
const schedulesQuery = useSchedulesQuery(scheduleFilters)
const scheduleMutations = useScheduleMutations()
const appsQuery = useAppsQuery(computed(() => ({})))
const devicesQuery = useDevicesQuery('all')

const schedules = computed(() => schedulesQuery.data.value?.items ?? [])
const total = computed(() => schedulesQuery.data.value?.total ?? 0)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))
const hasPreviousPage = computed(() => page.value > 1)
const hasNextPage = computed(() => page.value < totalPages.value)
const hasFilters = computed(() => Boolean(
  keyword.value.trim()
  || statusFilter.value !== 'all'
  || selectedAppId.value !== ALL_APPS_FILTER
))
const statusOptions = computed(() => [
  { value: 'all', label: t('schedules.filters.allStatus') },
  { value: 'enabled', label: t('schedules.filters.enabled') },
  { value: 'disabled', label: t('schedules.filters.disabled') },
])
const appOptions = computed(() => [
  { value: ALL_APPS_FILTER, label: t('schedules.filters.allApps') },
  ...((appsQuery.data.value ?? []).map((item) => ({
    value: item.app_id,
    label: item.app_id,
  }))),
])

const errorMessage = computed(() => {
  const error = schedulesQuery.error.value
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

watch([statusFilter, selectedAppId, keyword], () => {
  page.value = 1
})

function enabledTone(enabled: boolean) {
  return enabled ? 'success' as const : 'warning' as const
}

function nextRunLabel(value?: string | null) {
  return value ? time.relative(value) : '-'
}

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

async function handleToggle(scheduleId: string, enabled: boolean) {
  if (enabled) {
    await scheduleMutations.disableSchedule.mutateAsync(scheduleId)
    await schedulesQuery.refetch()
    return
  }
  await scheduleMutations.enableSchedule.mutateAsync(scheduleId)
  await schedulesQuery.refetch()
}

function deviceLabel(deviceRef: string | null | undefined): string {
  return formatDeviceLabel(deviceRef, devicesQuery.data.value ?? [], '-')
}
</script>

<template>
  <section class="app-page">
    <AppCard class="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto] md:items-start">
      <div class="grid gap-3 md:grid-cols-3">
        <UiSelect
          v-model="selectedAppId"
          :options="appOptions"
          :placeholder="t('schedules.filters.appPlaceholder')"
        />
        <UiSelect
          v-model="statusFilter"
          :options="statusOptions"
          :placeholder="t('schedules.filters.statusPlaceholder')"
        />
        <UiInput
          v-model="keyword"
          :placeholder="t('schedules.filters.keywordPlaceholder')"
        />
      </div>
      <div class="flex justify-end">
        <UiButton type="button" variant="secondary" @click="() => void schedulesQuery.refetch()">
          {{ t('schedules.actions.refresh') }}
        </UiButton>
      </div>
    </AppCard>

    <AppCard v-if="schedulesQuery.isFetching.value && schedules.length === 0">
      <p class="text-sm text-text-secondary">{{ t('common.loading') }}</p>
    </AppCard>

    <AppEmptyState
      v-else-if="errorMessage"
      :title="t('schedules.errorTitle')"
      :description="errorMessage"
    />

    <AppEmptyState
      v-else-if="schedules.length === 0 && !hasFilters"
      :title="t('schedules.emptyTitle')"
      :description="t('schedules.emptyDescription')"
    />

    <AppEmptyState
      v-else-if="schedules.length === 0"
      :title="t('schedules.filteredEmptyTitle')"
      :description="t('schedules.filteredEmptyDescription')"
    />

    <div v-else class="grid gap-3">
      <article
        v-for="item in schedules"
        :key="item.schedule_id"
        class="grid gap-4 rounded-lg border border-border-muted bg-surface-default p-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-start"
      >
        <div class="grid gap-3">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div class="flex flex-wrap items-center gap-2">
              <RouterLink class="text-base font-semibold text-text-primary transition-colors hover:text-accent" :to="`/schedules/${encodeURIComponent(item.schedule_id)}`">
                {{ item.name }}
              </RouterLink>
              <AppBadge :tone="enabledTone(item.enabled)">
                {{ item.enabled ? t('schedules.status.enabled') : t('schedules.status.disabled') }}
              </AppBadge>
            </div>
            <span class="text-sm text-text-secondary">{{ item.schedule_id }}</span>
          </div>
          <div class="flex flex-wrap gap-x-3 gap-y-2 text-sm text-text-secondary">
            <span>{{ t('schedules.fields.app') }}: {{ item.app_id }}</span>
            <span>{{ t('schedules.fields.device') }}: {{ deviceLabel(item.device_ref) }}</span>
            <span>{{ t('schedules.fields.cronExpr') }}: {{ item.cron_expr }}</span>
            <span>{{ t('schedules.fields.timezone') }}: {{ item.timezone }}</span>
            <span>{{ t('schedules.fields.nextRunAt') }}: {{ nextRunLabel(item.next_run_at) }}</span>
            <span>{{ t('schedules.fields.lastRunAt') }}: {{ item.last_run_at ? time.relative(item.last_run_at) : '-' }}</span>
          </div>
        </div>
        <div class="grid gap-2 sm:grid-cols-2 lg:grid-cols-1">
          <RouterLink
            class="inline-flex min-h-10 items-center justify-center rounded-xl border border-border bg-surface-default px-4 text-sm font-medium text-text-primary shadow-sm transition-all duration-150 hover:-translate-y-px hover:border-border-strong hover:bg-surface-muted"
            :to="`/schedules/${encodeURIComponent(item.schedule_id)}`"
          >
            {{ t('schedules.actions.openDetail') }}
          </RouterLink>
          <UiButton
            type="button"
            variant="secondary"
            :disabled="scheduleMutations.enableSchedule.isPending.value || scheduleMutations.disableSchedule.isPending.value"
            @click="() => void handleToggle(item.schedule_id, item.enabled)"
          >
            {{ item.enabled ? t('schedules.actions.disable') : t('schedules.actions.enable') }}
          </UiButton>
        </div>
      </article>
      <div
        v-if="totalPages > 1"
        class="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border-muted bg-surface-default px-4 py-3"
      >
        <span class="text-sm text-text-secondary">
          {{ t('schedules.pagination.pageStatus', { page, total: totalPages }) }}
        </span>
        <div class="flex items-center gap-2">
          <UiButton
            type="button"
            variant="secondary"
            :disabled="!hasPreviousPage"
            @click="goToPreviousPage"
          >
            {{ t('schedules.pagination.previousPage') }}
          </UiButton>
          <UiButton
            type="button"
            variant="secondary"
            :disabled="!hasNextPage"
            @click="goToNextPage"
          >
            {{ t('schedules.pagination.nextPage') }}
          </UiButton>
        </div>
      </div>
    </div>
  </section>
</template>
