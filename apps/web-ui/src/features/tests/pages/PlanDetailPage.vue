<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

import { createCaseRequest } from '@/features/tests/caseEditorForm'
import CreateCaseModal from '@/features/tests/components/CreateCaseModal.vue'
import { formatPlanVersionLabel } from '@/features/tests/version'
import AppBadge from '@/shared/components/AppBadge.vue'
import AppCard from '@/shared/components/AppCard.vue'
import AppEmptyState from '@/shared/components/AppEmptyState.vue'
import UiButton from '@/shared/ui/UiButton.vue'
import UiSelect from '@/shared/ui/UiSelect.vue'
import { LocalApiClientError } from '@/shared/api/client'
import { translateErrorCode } from '@/shared/i18n/errorMessages'
import { useDevicesQuery } from '@/features/devices/queries/useDevicesQuery'
import { useAppDetailQuery } from '@/features/apps/queries/useAppDetailQuery'
import { useAppsQuery } from '@/features/apps/queries/useAppsQuery'
import { useAddCaseMutation } from '@/features/tests/queries/useAddCaseMutation'
import { useDeleteCaseMutation } from '@/features/tests/queries/useDeleteCaseMutation'
import { usePlanDetailQuery } from '@/features/tests/queries/usePlanDetailQuery'
import { useRunPlanMutation } from '@/features/tests/queries/useRunPlanMutation'
import { formatPlanSourceLabel } from '@/features/tests/sourceLabels'
import { formatStartModeLabel } from '@/features/tests/startModeLabels'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()

const routeAppId = computed(() => String(route.params.appId ?? '').trim())
const planId = computed(() => String(route.params.planId))
const query = usePlanDetailQuery(routeAppId, planId)
const inferredAppId = computed(() => {
  const value = query.data.value?.app_id?.trim()
  return value || null
})
const selectedFallbackAppId = ref('')
const fallbackAppId = computed(() => selectedFallbackAppId.value.trim() || null)
const lookupAppId = computed(() => fallbackAppId.value ?? inferredAppId.value)
const appDetailQuery = useAppDetailQuery(lookupAppId)
const appsQuery = useAppsQuery(computed(() => ({})))
const platform = computed(() => appDetailQuery.data.value?.profile.platform ?? null)
const devicesQuery = useDevicesQuery(computed(() => platform.value ?? 'all'))
const runPlanMutation = useRunPlanMutation()
const addCaseMutation = useAddCaseMutation(routeAppId, planId)
const deleteCaseMutation = useDeleteCaseMutation(routeAppId, planId)
const selectedDeviceRef = ref('')
const createCaseOpen = ref(false)
const createCaseTitle = ref('')
const createCaseIntent = ref('')
const createCaseRunnerGoal = ref('')
const caseActionError = ref<string | null>(null)
const displayPlanName = computed(() => (
  query.data.value?.plan_name?.trim()
  || query.data.value?.plan_id
  || ''
))

function translateUnknownError(error: unknown): string | null {
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
}

const inferredAppMissing = computed(() => (
  Boolean(inferredAppId.value)
  && !fallbackAppId.value
  && appDetailQuery.error.value instanceof LocalApiClientError
  && appDetailQuery.error.value.code === 'app_not_found'
))

const needsAppSelection = computed(() => !inferredAppId.value || inferredAppMissing.value)
const effectiveAppId = computed(() => {
  if (fallbackAppId.value) {
    return fallbackAppId.value
  }
  if (needsAppSelection.value) {
    return null
  }
  return inferredAppId.value
})

const pageErrorMessage = computed(() => translateUnknownError(query.error.value))
const executionError = computed(() => {
  if (inferredAppMissing.value) {
    return null
  }
  return (
    translateUnknownError(appDetailQuery.error.value)
    ?? translateUnknownError(appsQuery.error.value)
    ?? translateUnknownError(devicesQuery.error.value)
  )
})

const submitError = computed(() => {
  return translateUnknownError(runPlanMutation.error.value)
})
const caseErrorMessage = computed(() => {
  return caseActionError.value
    ?? translateUnknownError(addCaseMutation.error.value)
    ?? translateUnknownError(deleteCaseMutation.error.value)
})

const appOptions = computed(() => (
  (appsQuery.data.value ?? []).map((item) => ({
    label: `${item.app_id} (${item.platform}${item.entry_identity ? ` / ${item.entry_identity}` : ''})`,
    value: item.app_id,
  }))
))

const deviceOptions = computed(() => (
  (devicesQuery.data.value ?? []).map((device) => ({
    label: `${device.display_name} (${device.platform})`,
    value: device.device_ref,
  }))
))

const requiresDeviceSelection = computed(() => platform.value === 'android' || platform.value === 'ios')
const runDisabled = computed(() => (
  runPlanMutation.isPending.value
  || !query.data.value
  || !effectiveAppId.value
  || !platform.value
  || (requiresDeviceSelection.value && !selectedDeviceRef.value)
))

async function handleRunPlan() {
  if (!query.data.value || !effectiveAppId.value || !platform.value || runDisabled.value) {
    return
  }
  const submission = await runPlanMutation.mutateAsync({
    app_id: effectiveAppId.value,
    plan_id: query.data.value.plan_id,
    fail_fast: false,
    headless: false,
    device_ref: selectedDeviceRef.value || null,
  })
  await router.push(`/runs/${encodeURIComponent(submission.operation_id)}`)
}

function openCreateCaseModal() {
  createCaseTitle.value = ''
  createCaseIntent.value = ''
  createCaseRunnerGoal.value = ''
  caseActionError.value = null
  addCaseMutation.reset()
  createCaseOpen.value = true
}

function closeCreateCaseModal() {
  if (addCaseMutation.isPending.value) {
    return
  }
  createCaseOpen.value = false
  createCaseTitle.value = ''
  createCaseIntent.value = ''
  createCaseRunnerGoal.value = ''
  caseActionError.value = null
  addCaseMutation.reset()
}

async function handleCreateCase() {
  if (!query.data.value) {
    return
  }
  caseActionError.value = null
  addCaseMutation.reset()
  try {
    const createdCase = await addCaseMutation.mutateAsync(createCaseRequest({
      title: createCaseTitle.value,
      intent: createCaseIntent.value,
      runnerGoal: createCaseRunnerGoal.value,
      existingCaseIds: (query.data.value.cases ?? []).map((item) => item.case_id),
    }))
    closeCreateCaseModal()
    await router.push(`/tests/plans/${encodeURIComponent(routeAppId.value)}/${encodeURIComponent(planId.value)}/cases/${encodeURIComponent(createdCase.case_id)}`)
  } catch (error) {
    if (!(error instanceof LocalApiClientError)) {
      caseActionError.value = translateUnknownError(error)
    }
  }
}

async function handleDeleteCase(caseId: string, title: string) {
  const confirmed = window.confirm(t('planDetail.deleteConfirm', { caseId, title }))
  if (!confirmed) {
    return
  }
  caseActionError.value = null
  deleteCaseMutation.reset()
  try {
    await deleteCaseMutation.mutateAsync(caseId)
  } catch (error) {
    if (!(error instanceof LocalApiClientError)) {
      caseActionError.value = translateUnknownError(error)
    }
  }
}
</script>

<template>
  <section class="app-page">
    <p v-if="query.isFetching.value" class="text-sm text-text-secondary">{{ t('common.loading') }}</p>
    <AppEmptyState
      v-else-if="pageErrorMessage"
      :title="t('planDetail.errorTitle')"
      :description="pageErrorMessage"
    />
    <template v-else-if="query.data.value">
      <AppCard class="grid gap-3">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div class="min-w-0 flex-1 grid gap-1">
            <div class="flex flex-wrap items-center gap-2">
              <h2 class="break-all text-xl font-semibold text-text-primary">{{ displayPlanName }}</h2>
              <AppBadge v-if="query.data.value.case_count === 1" tone="warning">
                {{ t('tests.plans.singleCasePlan') }}
              </AppBadge>
            </div>
            <p v-if="query.data.value.app_id?.trim()" class="text-sm text-text-secondary">
              {{ query.data.value.app_id }} / {{ query.data.value.plan_id }}
            </p>
          </div>
          <div class="flex min-w-72 justify-end">
            <div class="flex w-full max-w-xl items-center justify-end gap-3">
              <div v-if="needsAppSelection" class="min-w-56 flex-1 max-w-80">
                <UiSelect
                  v-model="selectedFallbackAppId"
                  :options="appOptions"
                  :disabled="appsQuery.isFetching.value"
                  :placeholder="t('planDetail.appSelectPlaceholder')"
                />
              </div>
              <div class="min-w-56 flex-1 max-w-80">
                <UiSelect
                  v-model="selectedDeviceRef"
                  :options="deviceOptions"
                  :disabled="devicesQuery.isFetching.value || !platform || (!deviceOptions.length && requiresDeviceSelection)"
                  :placeholder="t('planDetail.selectDevicePlaceholder')"
                />
              </div>
              <UiButton
                variant="primary"
                :disabled="runDisabled"
                @click="handleRunPlan"
              >
                {{ runPlanMutation.isPending.value ? t('planDetail.running') : t('planDetail.runAction') }}
              </UiButton>
            </div>
          </div>
        </div>
        <p v-if="needsAppSelection" class="text-sm text-text-secondary">{{ t('planDetail.appSelectHint') }}</p>
        <p v-else-if="platform" class="text-sm text-text-secondary">{{ t('planDetail.platformHint', { platform }) }}</p>
        <p v-if="executionError" class="text-sm text-danger">{{ executionError }}</p>
        <p v-if="submitError" class="text-sm text-danger">{{ submitError }}</p>
        <dl class="grid gap-4 md:grid-cols-3">
          <div class="grid min-w-0 gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
            <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('planDetail.fields.source') }}</dt>
            <dd class="break-all text-sm text-text-primary">{{ formatPlanSourceLabel(query.data.value.source, t) }}</dd>
          </div>
          <div class="grid min-w-0 gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
            <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('planDetail.fields.version') }}</dt>
            <dd class="break-all text-sm text-text-primary">{{ formatPlanVersionLabel(query.data.value.version) }}</dd>
          </div>
          <div class="grid min-w-0 gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
            <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('planDetail.fields.caseCount') }}</dt>
            <dd class="text-sm text-text-primary">{{ query.data.value.case_count }}</dd>
          </div>
        </dl>
      </AppCard>

      <AppCard class="grid gap-4">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div class="grid gap-2">
            <h2 class="app-section-title">{{ t('planDetail.casesTitle') }}</h2>
            <p class="app-section-description">{{ t('planDetail.casesDescription') }}</p>
          </div>
          <UiButton type="button" variant="primary" :disabled="addCaseMutation.isPending.value" @click="openCreateCaseModal">
            {{ t('planDetail.addCaseAction') }}
          </UiButton>
        </div>
        <p v-if="caseErrorMessage" class="text-sm text-error-text">{{ caseErrorMessage }}</p>
        <AppEmptyState
          v-if="(query.data.value.cases ?? []).length === 0"
          :title="t('planDetail.emptyTitle')"
          :description="t('planDetail.emptyDescription')"
        />
        <div v-else class="grid gap-3">
          <article
            v-for="item in query.data.value.cases ?? []"
            :key="item.case_id"
            class="grid gap-3 rounded-xl border border-border-muted bg-surface-muted p-4 md:grid-cols-[minmax(0,1fr)_auto] md:items-start"
          >
              <div class="min-w-0 grid gap-2">
                <RouterLink
                  class="break-words text-base font-semibold text-text-primary transition-colors hover:text-accent"
                  :to="`/tests/plans/${encodeURIComponent(routeAppId)}/${encodeURIComponent(query.data.value.plan_id)}/cases/${encodeURIComponent(item.case_id)}`"
                >
                  {{ item.title || item.case_id }}
                </RouterLink>
                <div class="flex flex-wrap items-center gap-x-3 gap-y-2 text-sm text-text-secondary">
                  <span>{{ item.intent }}</span>
                  <span>{{ formatStartModeLabel(item.start_mode, t) }}</span>
                  <AppBadge v-if="item.is_core_case" tone="success">
                    {{ t('planDetail.coreCase') }}
                  </AppBadge>
                </div>
              </div>
              <div class="flex items-center gap-2 md:justify-self-end">
                <UiButton
                  size="sm"
                  variant="secondary"
                  :disabled="deleteCaseMutation.isPending.value"
                  @click="router.push(`/tests/plans/${encodeURIComponent(routeAppId)}/${encodeURIComponent(query.data.value.plan_id)}/cases/${encodeURIComponent(item.case_id)}`)"
                >
                  {{ t('planDetail.openCaseAction') }}
                </UiButton>
                <UiButton
                  size="sm"
                  variant="ghost"
                  :disabled="deleteCaseMutation.isPending.value"
                  @click="handleDeleteCase(item.case_id, item.title)"
                >
                  {{ t('planDetail.deleteCaseAction') }}
                </UiButton>
              </div>
          </article>
        </div>
      </AppCard>
    </template>
    <CreateCaseModal
      :open="createCaseOpen"
      :title-value="createCaseTitle"
      :intent-value="createCaseIntent"
      :runner-goal-value="createCaseRunnerGoal"
      :creating="addCaseMutation.isPending.value"
      :error-message="caseErrorMessage"
      @close="closeCreateCaseModal"
      @confirm="handleCreateCase"
      @update:title-value="createCaseTitle = $event"
      @update:intent-value="createCaseIntent = $event"
      @update:runner-goal-value="createCaseRunnerGoal = $event"
    />
  </section>
</template>
