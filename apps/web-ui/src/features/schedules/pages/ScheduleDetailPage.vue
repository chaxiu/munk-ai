<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'

import AppBadge from '@/shared/components/AppBadge.vue'
import AppCard from '@/shared/components/AppCard.vue'
import CronEditorField from '@/shared/components/CronEditorField.vue'
import AppEmptyState from '@/shared/components/AppEmptyState.vue'
import { LocalApiClientError } from '@/shared/api/client'
import type { ScheduleRuntimeOverrides } from '@/shared/api/schedules'
import { translateErrorCode } from '@/shared/i18n/errorMessages'
import { useTime } from '@/shared/time/useTime'
import UiButton from '@/shared/ui/UiButton.vue'
import UiInput from '@/shared/ui/UiInput.vue'
import UiSelect from '@/shared/ui/UiSelect.vue'
import { formatDeviceLabel } from '@/features/devices/deviceLabels'
import { useDevicesQuery } from '@/features/devices/queries/useDevicesQuery'
import { useAppsQuery } from '@/features/apps/queries/useAppsQuery'
import { usePlansQuery } from '@/features/tests/queries/usePlansQuery'
import { useScheduleDetailQuery } from '../queries/useScheduleDetailQuery'
import { useScheduleMutations } from '../queries/useScheduleMutations'
import { useScheduleRunsQuery } from '../queries/useScheduleRunsQuery'

const route = useRoute()
const { t } = useI18n()
const time = useTime({ relative: true })
const scheduleId = computed(() => String(route.params.scheduleId))

const detailQuery = useScheduleDetailQuery(scheduleId)
const runsQuery = useScheduleRunsQuery(scheduleId, computed(() => ({ limit: 20 })))
const scheduleMutations = useScheduleMutations()
const appsQuery = useAppsQuery(computed(() => ({})))

const detail = computed(() => detailQuery.data.value)
const runs = computed(() => runsQuery.data.value?.items ?? [])
const isEditing = ref(false)
const editError = ref<string | null>(null)
const draftName = ref('')
const draftDeviceRef = ref('')
const draftCronExpr = ref('')
const draftCronHasError = ref(false)
const draftPlanIds = ref<string[]>([])
const draftEnabled = ref(true)

const selectedApp = computed(() => (
  (appsQuery.data.value ?? []).find((item) => item.app_id === detail.value?.app_id) ?? null
))
const devicesQuery = useDevicesQuery(computed(() => selectedApp.value?.platform ?? 'all'))
const plansQuery = usePlansQuery(computed(() => ({
  appId: detail.value?.app_id || undefined,
  limit: 100,
})))
const availablePlans = computed(() => plansQuery.data.value?.items ?? [])
const selectedPlans = computed(() => (
  draftPlanIds.value
    .map((planId) => availablePlans.value.find((item) => item.plan_id === planId))
    .filter((item): item is NonNullable<typeof item> => Boolean(item))
))
const deviceOptions = computed(() => (
  (devicesQuery.data.value ?? []).map((device) => ({
    label: `${device.display_name} (${device.platform})`,
    value: device.device_ref,
  }))
))
const saveDisabled = computed(() => (
  !detail.value
  || scheduleMutations.updateSchedule.isPending.value
  || !draftDeviceRef.value
  || draftPlanIds.value.length === 0
  || !draftCronExpr.value.trim()
  || draftCronHasError.value
))

const detailErrorMessage = computed(() => {
  const error = detailQuery.error.value
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

const runsErrorMessage = computed(() => {
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

function enabledTone(enabled: boolean) {
  return enabled ? 'success' as const : 'warning' as const
}

function booleanLabel(value: boolean) {
  return value ? t('schedules.status.enabled') : t('schedules.status.disabled')
}

function formatError(error: unknown): string {
  if (error instanceof LocalApiClientError) {
    return translateErrorCode(error.code, error.message)
  }
  if (error instanceof Error) {
    return error.message
  }
  return String(error)
}

function planDisplayName(planName?: string | null, planId?: string | null) {
  return planName?.trim() || planId?.trim() || ''
}

function planOrder(planId: string): number | null {
  const index = draftPlanIds.value.indexOf(planId)
  return index >= 0 ? index + 1 : null
}

const displayDeviceLabel = computed(() => (
  formatDeviceLabel(detail.value?.device_ref, devicesQuery.data.value ?? [], '-')
))

function togglePlan(planId: string) {
  editError.value = null
  const index = draftPlanIds.value.indexOf(planId)
  if (index >= 0) {
    draftPlanIds.value = draftPlanIds.value.filter((item) => item !== planId)
    return
  }
  draftPlanIds.value = [...draftPlanIds.value, planId]
}

function startEdit() {
  if (!detail.value) {
    return
  }
  draftName.value = detail.value.name
  draftDeviceRef.value = detail.value.device_ref
  draftCronExpr.value = detail.value.cron_expr
  draftCronHasError.value = false
  draftPlanIds.value = [...(detail.value.plan_ids ?? [])]
  draftEnabled.value = detail.value.enabled
  editError.value = null
  isEditing.value = true
}

function cancelEdit() {
  isEditing.value = false
  editError.value = null
  draftCronHasError.value = false
}

function normalizeRuntimeOverrides(
  value: Record<string, unknown> | null | undefined
): ScheduleRuntimeOverrides {
  if (!value) {
    return {}
  }
  return Object.fromEntries(
    Object.entries(value).filter(([, item]) => (
      typeof item === 'string'
      || typeof item === 'number'
      || typeof item === 'boolean'
    ))
  ) as ScheduleRuntimeOverrides
}

async function handleRefresh() {
  await Promise.all([
    detailQuery.refetch(),
    runsQuery.refetch(),
  ])
}

async function handleToggle() {
  if (!detail.value) {
    return
  }
  if (detail.value.enabled) {
    await scheduleMutations.disableSchedule.mutateAsync(detail.value.schedule_id)
  } else {
    await scheduleMutations.enableSchedule.mutateAsync(detail.value.schedule_id)
  }
  await handleRefresh()
}

async function saveEdit() {
  if (!detail.value || saveDisabled.value) {
    return
  }
  editError.value = null
  try {
    await scheduleMutations.updateSchedule.mutateAsync({
      scheduleId: detail.value.schedule_id,
      request: {
        name: draftName.value.trim() || undefined,
        app_id: detail.value.app_id,
        plan_ids: draftPlanIds.value,
        device_ref: draftDeviceRef.value,
        cron_expr: draftCronExpr.value.trim(),
        enabled: draftEnabled.value,
        timezone: detail.value.timezone,
        headless: detail.value.headless,
        fail_fast: detail.value.fail_fast,
        artifact_path: detail.value.artifact_path ?? undefined,
        assets_root: detail.value.assets_root ?? undefined,
        runtime_overrides: normalizeRuntimeOverrides(detail.value.runtime_overrides),
      },
    })
    isEditing.value = false
    await handleRefresh()
  } catch (error) {
    editError.value = formatError(error)
  }
}
</script>

<template>
  <section class="app-page">
    <AppCard v-if="detail" class="grid gap-4">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="grid gap-2">
          <div class="flex flex-wrap items-center gap-2">
            <h2 class="text-xl font-semibold text-text-primary">{{ detail.name || scheduleId }}</h2>
            <AppBadge :tone="enabledTone(detail.enabled)">
              {{ detail.enabled ? t('schedules.status.enabled') : t('schedules.status.disabled') }}
            </AppBadge>
          </div>
          <div class="flex flex-wrap gap-x-3 gap-y-2 text-sm text-text-secondary">
            <span>{{ detail.schedule_id }}</span>
            <span>{{ t('schedules.fields.app') }}: {{ detail.app_id }}</span>
            <span>{{ t('schedules.fields.device') }}: {{ displayDeviceLabel }}</span>
          </div>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <RouterLink
            class="inline-flex min-h-10 items-center justify-center rounded-xl border border-border bg-surface-default px-4 text-sm font-medium text-text-primary shadow-sm transition-all duration-150 hover:-translate-y-px hover:border-border-strong hover:bg-surface-muted"
            to="/schedules"
          >
            {{ t('schedules.actions.backToList') }}
          </RouterLink>
          <UiButton type="button" variant="secondary" @click="() => void handleRefresh()">
            {{ t('schedules.actions.refresh') }}
          </UiButton>
          <UiButton
            v-if="detail && !isEditing"
            type="button"
            variant="secondary"
            @click="startEdit"
          >
            {{ t('schedules.actions.edit') }}
          </UiButton>
          <UiButton
            v-if="detail && !isEditing"
            type="button"
            :variant="detail.enabled ? 'danger' : 'secondary'"
            :disabled="scheduleMutations.enableSchedule.isPending.value || scheduleMutations.disableSchedule.isPending.value"
            @click="() => void handleToggle()"
          >
            {{ detail.enabled ? t('schedules.actions.disable') : t('schedules.actions.enable') }}
          </UiButton>
          <UiButton
            v-if="isEditing"
            type="button"
            variant="ghost"
            @click="cancelEdit"
          >
            {{ t('schedules.actions.cancelEdit') }}
          </UiButton>
          <UiButton
            v-if="isEditing"
            type="button"
            variant="primary"
            :disabled="saveDisabled"
            @click="() => void saveEdit()"
          >
            {{ t('schedules.actions.save') }}
          </UiButton>
        </div>
      </div>
    </AppCard>

    <AppCard v-if="(detailQuery.isFetching.value || runsQuery.isFetching.value) && !detail">
      <p class="text-sm text-text-secondary">{{ t('common.loading') }}</p>
    </AppCard>

    <AppEmptyState
      v-else-if="detailErrorMessage"
      :title="t('schedules.errorTitle')"
      :description="detailErrorMessage"
    />

    <template v-else-if="detail">
      <AppCard v-if="!isEditing" class="grid gap-4">
        <dl class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          <div class="grid gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
            <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('schedules.fields.app') }}</dt>
            <dd class="text-sm text-text-primary">{{ detail.app_id }}</dd>
          </div>
          <div class="grid gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
            <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('schedules.fields.device') }}</dt>
            <dd class="text-sm text-text-primary">{{ displayDeviceLabel }}</dd>
          </div>
          <div class="grid gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
            <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('schedules.fields.planIds') }}</dt>
            <dd class="break-words text-sm text-text-primary">{{ detail.plan_ids?.join(', ') || '-' }}</dd>
          </div>
          <div class="grid gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
            <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('schedules.fields.cronExpr') }}</dt>
            <dd class="break-all text-sm text-text-primary">{{ detail.cron_expr }}</dd>
          </div>
          <div class="grid gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
            <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('schedules.fields.timezone') }}</dt>
            <dd class="text-sm text-text-primary">{{ detail.timezone }}</dd>
          </div>
          <div class="grid gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
            <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('schedules.fields.headless') }}</dt>
            <dd class="text-sm text-text-primary">{{ booleanLabel(detail.headless) }}</dd>
          </div>
          <div class="grid gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
            <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('schedules.fields.failFast') }}</dt>
            <dd class="text-sm text-text-primary">{{ booleanLabel(detail.fail_fast) }}</dd>
          </div>
          <div class="grid gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
            <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('schedules.fields.nextRunAt') }}</dt>
            <dd class="text-sm text-text-primary">{{ detail.next_run_at ? time.relative(detail.next_run_at) : '-' }}</dd>
          </div>
          <div class="grid gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
            <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('schedules.fields.lastRunAt') }}</dt>
            <dd class="text-sm text-text-primary">{{ detail.last_run_at ? time.relative(detail.last_run_at) : '-' }}</dd>
          </div>
          <div class="grid gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
            <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('schedules.fields.queuedRunCount') }}</dt>
            <dd class="text-sm text-text-primary">{{ detail.queued_run_count }}</dd>
          </div>
          <div class="grid gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
            <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('schedules.fields.activeRun') }}</dt>
            <dd class="break-all text-sm text-text-primary">{{ detail.active_schedule_run_id || '-' }}</dd>
          </div>
          <div class="grid gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
            <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('schedules.fields.latestOperation') }}</dt>
            <dd class="break-all text-sm text-text-primary">{{ detail.latest_operation_id || '-' }}</dd>
          </div>
          <div class="grid gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
            <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('schedules.fields.artifactPath') }}</dt>
            <dd class="break-all text-sm text-text-primary">{{ detail.artifact_path || '-' }}</dd>
          </div>
          <div class="grid gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
            <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('schedules.fields.assetsRoot') }}</dt>
            <dd class="break-all text-sm text-text-primary">{{ detail.assets_root || '-' }}</dd>
          </div>
          <div class="grid gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
            <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('schedules.fields.updatedAt') }}</dt>
            <dd class="text-sm text-text-primary">{{ time.relative(detail.updated_at) }}</dd>
          </div>
        </dl>
      </AppCard>

      <AppCard v-else class="grid gap-4">
        <div class="grid gap-3 md:grid-cols-2">
          <div class="grid gap-2 md:col-span-2">
            <label class="text-sm font-medium text-text-primary">{{ t('schedules.fields.name') }}</label>
            <UiInput v-model="draftName" />
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium text-text-primary">{{ t('schedules.fields.app') }}</label>
            <div class="min-h-11 rounded-xl border border-border bg-surface-muted px-3.5 py-2 text-sm text-text-secondary">
              {{ detail.app_id }}
            </div>
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium text-text-primary">{{ t('schedules.fields.device') }}</label>
            <UiSelect
              v-model="draftDeviceRef"
              :options="deviceOptions"
              :disabled="devicesQuery.isFetching.value"
              :placeholder="t('runsCreate.placeholders.device')"
            />
          </div>
          <div class="grid gap-2 md:col-span-2">
            <CronEditorField
              v-model="draftCronExpr"
              :label="t('schedules.fields.cronExpr')"
              :timezone="detail.timezone"
              @validation-change="draftCronHasError = $event"
            />
          </div>
        </div>
        <label class="flex items-start gap-3 rounded-xl border border-border-muted bg-surface-muted px-4 py-3">
          <input v-model="draftEnabled" type="checkbox" class="mt-1 h-4 w-4 rounded border-border">
          <span class="grid gap-1">
            <span class="text-sm font-medium text-text-primary">{{ t('schedules.fields.enabledToggle') }}</span>
            <span class="text-sm text-text-secondary">
              {{ draftEnabled ? t('schedules.status.enabled') : t('schedules.status.disabled') }}
            </span>
          </span>
        </label>
        <div class="grid gap-4 xl:grid-cols-[minmax(0,1.4fr)_minmax(320px,1fr)]">
          <div class="grid gap-4">
            <div class="grid gap-1">
              <h3 class="app-section-title">{{ t('runsCreate.availablePlansTitle') }}</h3>
              <p class="app-section-description">{{ t('runsCreate.availablePlansDescription') }}</p>
            </div>
            <AppEmptyState
              v-if="plansQuery.isFetching.value && availablePlans.length === 0"
              :title="t('common.loading')"
              :description="''"
            />
            <AppEmptyState
              v-else-if="availablePlans.length === 0"
              :title="t('runsCreate.emptyPlansTitle')"
              :description="t('runsCreate.emptyPlansDescription')"
            />
            <div v-else class="grid gap-3">
              <button
                v-for="plan in availablePlans"
                :key="plan.plan_id"
                type="button"
                class="grid gap-2 rounded-xl border px-4 py-3 text-left transition-colors"
                :class="planOrder(plan.plan_id) ? 'border-accent bg-accent/5' : 'border-border-muted bg-surface-default hover:border-border-strong'"
                @click="togglePlan(plan.plan_id)"
              >
                <div class="flex items-start justify-between gap-3">
                  <div class="min-w-0 grid gap-1">
                    <strong class="break-words text-sm text-text-primary">
                      {{ planDisplayName(plan.plan_name, plan.plan_id) }}
                    </strong>
                    <div class="flex flex-wrap gap-x-3 gap-y-1 text-sm text-text-secondary">
                      <span>{{ plan.plan_id }}</span>
                      <span>{{ t('tests.plans.caseCount', { count: plan.case_count }) }}</span>
                    </div>
                  </div>
                  <span
                    v-if="planOrder(plan.plan_id)"
                    class="inline-flex min-h-7 min-w-7 items-center justify-center rounded-full bg-accent px-2 text-xs font-semibold text-white"
                  >
                    {{ planOrder(plan.plan_id) }}
                  </span>
                </div>
              </button>
            </div>
          </div>
          <div class="grid content-start gap-4">
            <div class="grid gap-1">
              <h3 class="app-section-title">{{ t('schedules.fields.planIds') }}</h3>
              <p class="app-section-description">{{ t('runsCreate.selectionDescription') }}</p>
            </div>
            <AppEmptyState
              v-if="selectedPlans.length === 0"
              :title="t('runsCreate.emptySelectionTitle')"
              :description="t('runsCreate.emptySelectionDescription')"
            />
            <div v-else class="grid gap-3">
              <article
                v-for="(plan, index) in selectedPlans"
                :key="plan.plan_id"
                class="grid gap-2 rounded-xl border border-border-muted bg-surface-muted p-3"
              >
                <div class="flex items-start gap-3">
                  <span class="inline-flex min-h-7 min-w-7 items-center justify-center rounded-full bg-accent px-2 text-xs font-semibold text-white">
                    {{ index + 1 }}
                  </span>
                  <div class="min-w-0 grid gap-1">
                    <strong class="break-words text-sm text-text-primary">
                      {{ planDisplayName(plan.plan_name, plan.plan_id) }}
                    </strong>
                    <span class="text-sm text-text-secondary">{{ plan.plan_id }}</span>
                  </div>
                </div>
              </article>
            </div>
          </div>
        </div>
        <p v-if="editError" class="text-sm text-error-text">{{ editError }}</p>
      </AppCard>

      <AppCard class="grid gap-4">
        <div class="grid gap-1">
          <h2 class="app-section-title">{{ t('schedules.historyTitle') }}</h2>
        </div>
        <p v-if="runsErrorMessage" class="text-sm text-error-text">{{ runsErrorMessage }}</p>
        <AppEmptyState
          v-else-if="runs.length === 0"
          :title="t('schedules.historyEmptyTitle')"
          :description="t('schedules.historyEmptyDescription')"
        />
        <div v-else class="grid gap-3">
          <article
            v-for="item in runs"
            :key="item.schedule_run_id"
            class="grid gap-3 rounded-xl border border-border-muted bg-surface-muted p-4 md:grid-cols-[minmax(0,1fr)_auto]"
          >
            <div class="grid gap-2">
              <div class="flex flex-wrap items-center gap-2">
                <AppBadge>{{ item.status }}</AppBadge>
                <span class="text-sm text-text-secondary">{{ item.schedule_run_id }}</span>
              </div>
              <div class="grid gap-2 text-sm text-text-secondary md:grid-cols-2 xl:grid-cols-3">
                <span>{{ t('schedules.fields.scheduledFor') }}: {{ time.relative(item.scheduled_for) }}</span>
                <span>{{ t('schedules.fields.createdAt') }}: {{ time.relative(item.created_at) }}</span>
                <span>{{ t('schedules.fields.triggeredAt') }}: {{ item.triggered_at ? time.relative(item.triggered_at) : '-' }}</span>
                <span>{{ t('schedules.fields.startedAt') }}: {{ item.started_at ? time.relative(item.started_at) : '-' }}</span>
                <span>{{ t('schedules.fields.finishedAt') }}: {{ item.finished_at ? time.relative(item.finished_at) : '-' }}</span>
                <span>{{ t('schedules.fields.operationId') }}: {{ item.operation_id || '-' }}</span>
              </div>
              <div v-if="item.error_code || item.error_message" class="grid gap-1 text-sm text-error-text">
                <span v-if="item.error_code">{{ item.error_code }}</span>
                <span v-if="item.error_message">{{ item.error_message }}</span>
              </div>
            </div>
            <div class="flex items-center gap-2 md:justify-self-end">
              <RouterLink
                v-if="item.operation_id"
                class="inline-flex min-h-10 items-center justify-center rounded-xl border border-border bg-surface-default px-4 text-sm font-medium text-text-primary shadow-sm transition-all duration-150 hover:-translate-y-px hover:border-border-strong hover:bg-surface-muted"
                :to="`/runs/${encodeURIComponent(item.operation_id)}`"
              >
                {{ t('schedules.actions.openRun') }}
              </RouterLink>
            </div>
          </article>
        </div>
      </AppCard>
    </template>
  </section>
</template>
