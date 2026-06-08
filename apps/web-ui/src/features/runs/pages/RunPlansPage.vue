<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useQueryClient } from '@tanstack/vue-query'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import AppCard from '@/shared/components/AppCard.vue'
import CronEditorField from '@/shared/components/CronEditorField.vue'
import AppEmptyState from '@/shared/components/AppEmptyState.vue'
import UiInput from '@/shared/ui/UiInput.vue'
import UiButton from '@/shared/ui/UiButton.vue'
import UiSelect from '@/shared/ui/UiSelect.vue'
import { LocalApiClientError } from '@/shared/api/client'
import { createSchedule } from '@/shared/api/schedules'
import { submitRunPlans } from '@/shared/api/workflows'
import { translateErrorCode } from '@/shared/i18n/errorMessages'
import { schedulesKeys } from '@/features/schedules/queries/schedulesKeys'
import { useDevicesQuery } from '@/features/devices/queries/useDevicesQuery'
import { useAppsQuery } from '@/features/apps/queries/useAppsQuery'
import { usePlansQuery } from '@/features/tests/queries/usePlansQuery'

const router = useRouter()
const queryClient = useQueryClient()
const { t } = useI18n()

const taskName = ref('')
const scheduleEnabled = ref(false)
const cronExpr = ref('')
const cronHasError = ref(false)
const selectedAppId = ref('')
const selectedDeviceRef = ref('')
const selectedPlanIds = ref<string[]>([])
const submitError = ref<string | null>(null)
const submitting = ref(false)

const appsQuery = useAppsQuery(computed(() => ({})))
const selectedApp = computed(() => (
  (appsQuery.data.value ?? []).find((item) => item.app_id === selectedAppId.value) ?? null
))
const plansQuery = usePlansQuery(computed(() => ({
  appId: selectedAppId.value || undefined,
  limit: 100,
})))
const devicesQuery = useDevicesQuery(computed(() => selectedApp.value?.platform ?? 'all'))

watch(selectedAppId, () => {
  selectedPlanIds.value = []
  selectedDeviceRef.value = ''
  submitError.value = null
})

watch(scheduleEnabled, (enabled) => {
  if (!enabled) {
    cronHasError.value = false
  }
})

const appOptions = computed(() => (
  (appsQuery.data.value ?? []).map((item) => ({
    label: `${item.app_id} (${item.platform})`,
    value: item.app_id,
  }))
))

const deviceOptions = computed(() => (
  (devicesQuery.data.value ?? []).map((device) => ({
    label: `${device.display_name} (${device.platform})`,
    value: device.device_ref,
  }))
))

const availablePlans = computed(() => plansQuery.data.value?.items ?? [])
const selectedPlans = computed(() => (
  selectedPlanIds.value
    .map((planId) => availablePlans.value.find((item) => item.plan_id === planId))
    .filter((item): item is NonNullable<typeof item> => Boolean(item))
))
const runDisabled = computed(() => (
  submitting.value
  || !selectedAppId.value
  || !selectedDeviceRef.value
  || selectedPlanIds.value.length === 0
  || (scheduleEnabled.value && (!cronExpr.value.trim() || cronHasError.value))
))
const submitLabel = computed(() => (
  scheduleEnabled.value ? t('runsCreate.scheduleSubmit') : t('runsCreate.runSubmit')
))
const submittingLabel = computed(() => (
  scheduleEnabled.value ? t('runsCreate.scheduleSubmitting') : t('runsCreate.submitting')
))

function resolveLocalTimezone(): string | undefined {
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone?.trim()
  return timezone || undefined
}

function planDisplayName(planName?: string | null, planId?: string | null) {
  return planName?.trim() || planId?.trim() || ''
}

function planOrder(planId: string): number | null {
  const index = selectedPlanIds.value.indexOf(planId)
  return index >= 0 ? index + 1 : null
}

function togglePlan(planId: string) {
  submitError.value = null
  const index = selectedPlanIds.value.indexOf(planId)
  if (index >= 0) {
    selectedPlanIds.value = selectedPlanIds.value.filter((item) => item !== planId)
    return
  }
  selectedPlanIds.value = [...selectedPlanIds.value, planId]
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

async function handleSubmit() {
  if (runDisabled.value) {
    return
  }
  submitError.value = null
  submitting.value = true
  try {
    if (scheduleEnabled.value) {
      await createSchedule({
        name: taskName.value.trim() || undefined,
        app_id: selectedAppId.value,
        plan_ids: selectedPlanIds.value,
        device_ref: selectedDeviceRef.value,
        timezone: resolveLocalTimezone(),
        cron_expr: cronExpr.value.trim(),
        enabled: true,
        fail_fast: false,
        headless: false,
      })
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: schedulesKeys.list() }),
        queryClient.invalidateQueries({ queryKey: schedulesKeys.all }),
      ])
      await router.push('/schedules')
      return
    }

    const result = await submitRunPlans({
      app_id: selectedAppId.value,
      plan_ids: selectedPlanIds.value,
      device_ref: selectedDeviceRef.value,
      fail_fast: false,
      headless: false,
    }, { wait: false, detach: false })
    await router.push(`/runs/${encodeURIComponent(result.operation_id)}`)
  } catch (error) {
    submitError.value = formatError(error)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section class="app-page">
    <AppCard class="grid gap-4">
      <div class="grid gap-1">
        <h2 class="app-section-title">{{ t('runsCreate.title') }}</h2>
        <p class="app-section-description">{{ t('runsCreate.description') }}</p>
      </div>
      <div class="grid gap-3 md:grid-cols-2">
        <div class="grid gap-2 md:col-span-2">
          <label class="text-sm font-medium text-text-primary">{{ t('runsCreate.fields.name') }}</label>
          <UiInput
            v-model="taskName"
            :placeholder="t('runsCreate.placeholders.name')"
          />
        </div>
        <div class="grid gap-2">
          <label class="text-sm font-medium text-text-primary">{{ t('runsCreate.fields.app') }}</label>
          <UiSelect
            v-model="selectedAppId"
            :options="appOptions"
            :disabled="appsQuery.isFetching.value"
            :placeholder="t('runsCreate.placeholders.app')"
          />
        </div>
        <div class="grid gap-2">
          <label class="text-sm font-medium text-text-primary">{{ t('runsCreate.fields.device') }}</label>
          <UiSelect
            v-model="selectedDeviceRef"
            :options="deviceOptions"
            :disabled="devicesQuery.isFetching.value || !selectedApp"
            :placeholder="t('runsCreate.placeholders.device')"
          />
        </div>
      </div>
      <label class="flex items-start gap-3 rounded-xl border border-border-muted bg-surface-muted px-4 py-3">
        <input v-model="scheduleEnabled" type="checkbox" class="mt-1 h-4 w-4 rounded border-border">
        <span class="grid gap-1">
          <span class="text-sm font-medium text-text-primary">{{ t('runsCreate.fields.scheduleEnabled') }}</span>
          <span class="text-sm text-text-secondary">{{ t('runsCreate.scheduleDescription') }}</span>
        </span>
      </label>
      <div v-if="scheduleEnabled" class="grid gap-2">
        <CronEditorField
          v-model="cronExpr"
          :label="t('runsCreate.fields.cronExpr')"
          :placeholder="t('runsCreate.placeholders.cronExpr')"
          @validation-change="cronHasError = $event"
        />
      </div>
      <p v-if="submitError" class="text-sm text-error-text">{{ submitError }}</p>
    </AppCard>

    <div class="grid gap-4 xl:grid-cols-[minmax(0,1.4fr)_minmax(320px,1fr)]">
      <AppCard class="grid gap-4">
        <div class="grid gap-1">
          <h2 class="app-section-title">{{ t('runsCreate.availablePlansTitle') }}</h2>
          <p class="app-section-description">{{ t('runsCreate.availablePlansDescription') }}</p>
        </div>
        <AppEmptyState
          v-if="!selectedAppId"
          :title="t('runsCreate.emptyAppTitle')"
          :description="t('runsCreate.emptyAppDescription')"
        />
        <p v-else-if="plansQuery.isFetching.value" class="text-sm text-text-secondary">{{ t('common.loading') }}</p>
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
      </AppCard>

      <AppCard class="grid content-start gap-4">
        <div class="grid gap-1">
          <h2 class="app-section-title">{{ t('runsCreate.selectionTitle') }}</h2>
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
        <UiButton variant="primary" :disabled="runDisabled" @click="handleSubmit">
          {{ submitting ? submittingLabel : submitLabel }}
        </UiButton>
      </AppCard>
    </div>
  </section>
</template>
