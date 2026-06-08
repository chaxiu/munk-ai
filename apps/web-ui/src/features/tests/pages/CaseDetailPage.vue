<script setup lang="ts">
import { Play, Smartphone } from '@lucide/vue'
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useQuery } from '@tanstack/vue-query'

import AppBadge from '@/shared/components/AppBadge.vue'
import AppCard from '@/shared/components/AppCard.vue'
import AppEmptyState from '@/shared/components/AppEmptyState.vue'
import CaseRewritePreviewModal from '@/features/tests/components/CaseRewritePreviewModal.vue'
import UiButton from '@/shared/ui/UiButton.vue'
import UiField from '@/shared/ui/UiField.vue'
import UiInput from '@/shared/ui/UiInput.vue'
import UiSelect from '@/shared/ui/UiSelect.vue'
import UiTextarea from '@/shared/ui/UiTextarea.vue'
import type { CaseRewritePreviewData } from '@/shared/api/tests'
import { LocalApiClientError } from '@/shared/api/client'
import { type OperationSummaryData, listOperations } from '@/shared/api/operations'
import { type CaseEditorFormModel, buildCaseUpsertRequest, createCaseEditorForm, createCaseEditorFormFromPayload } from '@/features/tests/caseEditorForm'
import { formatDeviceLabel } from '@/features/devices/deviceLabels'
import { useDevicesQuery } from '@/features/devices/queries/useDevicesQuery'
import { useAppDetailQuery } from '@/features/apps/queries/useAppDetailQuery'
import { useAppsQuery } from '@/features/apps/queries/useAppsQuery'
import { useCaseDetailQuery } from '@/features/tests/queries/useCaseDetailQuery'
import { useRewriteCasePreviewMutation } from '@/features/tests/queries/useRewriteCasePreviewMutation'
import { useReplaceCaseMutation } from '@/features/tests/queries/useReplaceCaseMutation'
import { formatPlanVersionLabel } from '@/features/tests/version'
import { formatPlanSourceLabel } from '@/features/tests/sourceLabels'
import { formatStartModeLabel } from '@/features/tests/startModeLabels'
import { submitRunCase } from '@/shared/api/workflows'
import { translateErrorCode } from '@/shared/i18n/errorMessages'
import { useTime } from '@/shared/time/useTime'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const time = useTime({ relative: true })

const appId = computed(() => String(route.params.appId))
const planId = computed(() => String(route.params.planId))
const caseId = computed(() => String(route.params.caseId))

const query = useCaseDetailQuery(appId, planId, caseId)
const devicesQuery = useDevicesQuery('all')
const appsQuery = useAppsQuery(computed(() => ({ platform: 'android' })))
const packageName = ref('')
const selectedDeviceRef = ref('')
const selectedFallbackAppId = ref('')
const submitting = ref(false)
const submitError = ref<string | null>(null)
const saveError = ref<string | null>(null)
const rewritePrompt = ref('')
const rewritePreview = ref<CaseRewritePreviewData | null>(null)
const rewriteError = ref<string | null>(null)
const rewriteModalOpen = ref(false)
const rewriteCasePreviewMutation = useRewriteCasePreviewMutation(appId, planId, caseId)
const replaceCaseMutation = useReplaceCaseMutation(appId, planId, caseId)
const form = reactive<CaseEditorFormModel>({
  title: '',
  intent: '',
  runnerGoal: '',
  preconditionsText: '',
  expectedText: '',
  procedureText: '',
  postActionText: '',
  isCoreCase: false,
  startMode: 'reset',
  startPageId: '',
  maxSteps: '',
  maxSeconds: '',
})

const inferredAppId = computed(() => {
  const fromCase = query.data.value?.app_id?.trim()
  if (fromCase) {
    return fromCase
  }
  const fromRoute = String(route.params.appId ?? '').trim()
  return fromRoute || null
})

const effectiveAppId = computed(() => inferredAppId.value ?? (selectedFallbackAppId.value.trim() || null))
const appDetailQuery = useAppDetailQuery(effectiveAppId)

const appOptions = computed(() => (
  (appsQuery.data.value ?? []).map((item) => ({
    label: `${item.app_id} (${item.platform}${item.entry_identity ? ` / ${item.entry_identity}` : ''})`,
    value: item.app_id,
  }))
))

const selectedAppDetail = computed(() => appDetailQuery.data.value)
const resolvedPackageName = computed(() => selectedAppDetail.value?.profile.android?.package_name?.trim() ?? '')
const needsAppSelection = computed(() => !inferredAppId.value)
const needsPackageInput = computed(() => !resolvedPackageName.value)

const recentRunsQuery = useQuery({
  queryKey: ['tests', 'recent-runs', appId.value, planId.value, caseId.value],
  queryFn: () => listOperations({ limit: 50, surface: 'run_center' }),
})

const recentRuns = computed(() => (recentRunsQuery.data.value ?? []).filter((item) => (
  item.app_id === appId.value
  && item.plan_id === planId.value
  && item.case_id === caseId.value
)).slice(0, 5))
const latestOptimize = computed(() => query.data.value?.latest_optimize ?? null)
const latestOptimizeUpdatedAt = computed(() => (
  latestOptimize.value?.finished_at
  ?? latestOptimize.value?.started_at
  ?? latestOptimize.value?.created_at
  ?? null
))

const errorMessage = computed(() => {
  const error = query.error.value
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

const runDisabled = computed(() => (
  submitting.value
  || !selectedDeviceRef.value
  || !effectiveAppId.value
  || !packageName.value.trim()
))

const deviceOptions = computed(() => (
  (devicesQuery.data.value ?? []).map((device) => ({
    label: `${device.display_name} (${device.platform})`,
    value: device.device_ref,
  }))
))
const saveErrorMessage = computed(() => saveError.value ?? translateUnknownError(replaceCaseMutation.error.value))
const saveDisabled = computed(() => replaceCaseMutation.isPending.value || !query.data.value)
const rewriteGenerateDisabled = computed(() => rewriteCasePreviewMutation.isPending.value || !rewritePrompt.value.trim())
const startModeOptions = computed(() => ([
  { label: formatStartModeLabel('reset', t), value: 'reset' },
  { label: formatStartModeLabel('resume', t), value: 'resume' },
]))

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

watch(effectiveAppId, () => {
  packageName.value = ''
  submitError.value = null
})

watch(resolvedPackageName, (value) => {
  if (value) {
    packageName.value = value
  }
}, { immediate: true })

watch(() => query.data.value, (detail) => {
  if (!detail) {
    return
  }
  Object.assign(form, createCaseEditorForm(detail))
  saveError.value = null
}, { immediate: true })

function openRewriteModal() {
  rewriteModalOpen.value = true
  rewriteError.value = null
}

function closeRewriteModal() {
  if (rewriteCasePreviewMutation.isPending.value) {
    return
  }
  rewriteModalOpen.value = false
}

async function handleGenerateRewritePreview() {
  if (rewriteGenerateDisabled.value) {
    return
  }
  rewriteError.value = null
  rewritePreview.value = null
  rewriteCasePreviewMutation.reset()
  try {
    rewritePreview.value = await rewriteCasePreviewMutation.mutateAsync({ prompt: rewritePrompt.value.trim() })
  } catch (error) {
    rewriteError.value = translateUnknownError(error)
  }
}

function handleApplyRewritePreview() {
  if (!rewritePreview.value) {
    return
  }
  Object.assign(form, createCaseEditorFormFromPayload(rewritePreview.value.case))
  rewriteModalOpen.value = false
}

function runTone(item: OperationSummaryData): 'neutral' | 'success' | 'error' | 'warning' {
  if (item.status === 'succeeded') {
    return 'success'
  }
  if (item.status === 'failed') {
    return 'error'
  }
  if (item.status === 'running') {
    return 'warning'
  }
  return 'neutral'
}

function deviceLabel(deviceRef: string | null | undefined): string {
  return formatDeviceLabel(deviceRef, devicesQuery.data.value ?? [], t('home.unassignedDevice'))
}

function optimizeTone(status: string | null | undefined): 'neutral' | 'success' | 'error' | 'warning' {
  if (status === 'succeeded') {
    return 'success'
  }
  if (status === 'failed') {
    return 'error'
  }
  if (status === 'queued' || status === 'running') {
    return 'warning'
  }
  return 'neutral'
}

async function handleRunCase() {
  submitError.value = null
  submitting.value = true
  try {
    const submission = await submitRunCase(
      {
        app_id: String(effectiveAppId.value),
        plan_id: planId.value,
        case_id: caseId.value,
        device_ref: selectedDeviceRef.value,
        package: packageName.value.trim(),
      },
      { wait: false, detach: false }
    )
    await router.push(`/runs/${encodeURIComponent(submission.operation_id)}`)
  } catch (error) {
    if (error instanceof LocalApiClientError) {
      submitError.value = translateErrorCode(error.code, error.message)
    } else if (error instanceof Error) {
      submitError.value = error.message
    } else {
      submitError.value = String(error)
    }
  } finally {
    submitting.value = false
  }
}

async function handleSaveCase() {
  if (!query.data.value) {
    return
  }
  saveError.value = null
  replaceCaseMutation.reset()
  try {
    await replaceCaseMutation.mutateAsync(buildCaseUpsertRequest(form, caseId.value))
  } catch (error) {
    if (!(error instanceof LocalApiClientError)) {
      saveError.value = translateUnknownError(error)
    }
  }
}
</script>

<template>
  <section class="app-page">
    <p v-if="query.isFetching.value" class="text-sm text-text-secondary">{{ t('common.loading') }}</p>
    <AppEmptyState
      v-else-if="errorMessage"
      :title="t('caseDetail.errorTitle')"
      :description="errorMessage"
    />
    <template v-else-if="query.data.value">
      <AppCard class="grid gap-4">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div class="min-w-0 flex-1">
            <h2 class="break-words text-xl font-semibold text-text-primary">{{ query.data.value.title }}</h2>
            <div class="mt-2 flex flex-wrap gap-x-3 gap-y-2 text-sm text-text-secondary">
              <span class="break-all">{{ query.data.value.case_id }}</span>
              <span>{{ formatPlanSourceLabel(query.data.value.plan_source, t) }}</span>
            </div>
          </div>
          <AppBadge v-if="query.data.value.is_core_case" tone="success">
            {{ t('caseDetail.coreCase') }}
          </AppBadge>
        </div>
        <dl class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div class="grid min-w-0 gap-1 overflow-hidden rounded-xl border border-border-muted bg-surface-muted p-4">
            <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('caseDetail.fields.caseId') }}</dt>
            <dd class="break-all text-sm text-text-primary">{{ query.data.value.case_id }}</dd>
          </div>
          <div class="grid min-w-0 gap-1 overflow-hidden rounded-xl border border-border-muted bg-surface-muted p-4">
            <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('caseDetail.fields.planSource') }}</dt>
            <dd class="break-all text-sm text-text-primary">{{ formatPlanSourceLabel(query.data.value.plan_source, t) }}</dd>
          </div>
          <div class="grid min-w-0 gap-1 overflow-hidden rounded-xl border border-border-muted bg-surface-muted p-4">
            <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('caseDetail.fields.planVersion') }}</dt>
            <dd class="break-all text-sm text-text-primary">{{ formatPlanVersionLabel(query.data.value.plan_version) }}</dd>
          </div>
          <div class="grid min-w-0 gap-1 overflow-hidden rounded-xl border border-border-muted bg-surface-muted p-4">
            <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('caseDetail.fields.appId') }}</dt>
            <dd class="break-all text-sm text-text-primary">{{ query.data.value.app_id || t('recording.none') }}</dd>
          </div>
        </dl>
      </AppCard>

      <AppCard class="grid gap-4">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div class="grid gap-2">
            <h2 class="app-section-title">{{ t('caseDetail.contentTitle') }}</h2>
            <p class="app-section-description">{{ t('caseDetail.editorDescription') }}</p>
          </div>
          <div class="flex flex-wrap gap-2">
            <UiButton type="button" variant="secondary" :disabled="replaceCaseMutation.isPending.value" @click="openRewriteModal">
              {{ t('caseDetail.aiRewriteAction') }}
            </UiButton>
            <UiButton type="button" variant="primary" :disabled="saveDisabled" @click="handleSaveCase">
              {{ replaceCaseMutation.isPending.value ? t('caseDetail.saving') : t('caseDetail.saveChanges') }}
            </UiButton>
          </div>
        </div>
        <p v-if="saveErrorMessage" class="text-sm text-error-text">{{ saveErrorMessage }}</p>
        <div class="grid gap-4 md:grid-cols-2">
          <UiField :label="t('caseDetail.fields.title')">
            <UiInput v-model="form.title" :disabled="replaceCaseMutation.isPending.value" />
          </UiField>
          <UiField :label="t('caseDetail.fields.runnerGoal')">
            <UiInput v-model="form.runnerGoal" :disabled="replaceCaseMutation.isPending.value" />
          </UiField>
        </div>
        <UiField :label="t('caseDetail.fields.intent')">
          <UiTextarea v-model="form.intent" :rows="4" :disabled="replaceCaseMutation.isPending.value" />
        </UiField>
        <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <UiField :label="t('caseDetail.fields.startMode')">
            <UiSelect
              v-model="form.startMode"
              :options="startModeOptions"
              :placeholder="t('caseDetail.startModePlaceholder')"
              :disabled="replaceCaseMutation.isPending.value"
            />
          </UiField>
          <UiField :label="t('caseDetail.fields.startPageId')">
            <UiInput v-model="form.startPageId" :disabled="replaceCaseMutation.isPending.value" />
          </UiField>
          <UiField :label="t('caseDetail.fields.maxSteps')">
            <UiInput v-model="form.maxSteps" type="number" min="0" step="1" :disabled="replaceCaseMutation.isPending.value" />
          </UiField>
          <UiField :label="t('caseDetail.fields.maxSeconds')">
            <UiInput v-model="form.maxSeconds" type="number" min="0" step="1" :disabled="replaceCaseMutation.isPending.value" />
          </UiField>
        </div>
        <label class="inline-flex items-center gap-2 text-sm text-text-primary">
          <input
            v-model="form.isCoreCase"
            type="checkbox"
            class="h-4 w-4 rounded border-border"
            :disabled="replaceCaseMutation.isPending.value"
          >
          <span>{{ t('caseDetail.fields.isCoreCase') }}</span>
        </label>
        <div class="grid gap-4 xl:grid-cols-4">
          <UiField :label="t('caseDetail.fields.preconditions')">
            <UiTextarea v-model="form.preconditionsText" :rows="8" :disabled="replaceCaseMutation.isPending.value" />
          </UiField>
          <UiField :label="t('caseDetail.fields.expected')">
            <UiTextarea v-model="form.expectedText" :rows="8" :disabled="replaceCaseMutation.isPending.value" />
          </UiField>
          <UiField :label="t('caseDetail.fields.procedure')">
            <UiTextarea v-model="form.procedureText" :rows="8" :disabled="replaceCaseMutation.isPending.value" />
          </UiField>
          <UiField :label="t('caseDetail.fields.postAction')">
            <UiTextarea v-model="form.postActionText" :rows="8" :disabled="replaceCaseMutation.isPending.value" />
          </UiField>
        </div>
      </AppCard>

      <AppCard class="grid gap-4">
        <h2 class="app-section-title">{{ t('caseDetail.executionTitle') }}</h2>
        <p class="app-section-description">{{ t('caseDetail.executionDescription') }}</p>
        <div class="grid gap-4 md:grid-cols-2">
          <UiField v-if="needsAppSelection" :label="t('caseDetail.appFieldLabel')">
            <UiSelect
              v-model="selectedFallbackAppId"
              :options="appOptions"
              :placeholder="t('caseDetail.appSelectPlaceholder')"
              :disabled="appsQuery.isFetching.value"
            />
          </UiField>
          <UiField v-else :label="t('caseDetail.appFieldLabel')">
            <UiInput :model-value="effectiveAppId ?? ''" :disabled="true" />
          </UiField>
          <UiField :label="t('caseDetail.selectDevicePlaceholder')">
            <UiSelect v-model="selectedDeviceRef" :options="deviceOptions" :placeholder="t('caseDetail.selectDevicePlaceholder')" />
          </UiField>
          <UiField :label="t('caseDetail.packageFieldLabel')">
            <UiInput
              v-model="packageName"
              :placeholder="t('caseDetail.packagePlaceholder')"
              :disabled="!needsPackageInput"
            />
          </UiField>
        </div>
        <p v-if="needsAppSelection" class="text-sm text-text-secondary">{{ t('caseDetail.appSelectHint') }}</p>
        <p v-else class="text-sm text-text-secondary">{{ t('caseDetail.appResolvedHint') }}</p>
        <p class="text-sm text-text-secondary">
          {{ needsPackageInput ? t('caseDetail.packageManualHint') : t('caseDetail.packageResolvedHint') }}
        </p>
        <p v-if="submitError" class="text-sm text-error-text">{{ submitError }}</p>
        <div class="flex justify-end">
          <UiButton type="button" variant="primary" :disabled="runDisabled" @click="handleRunCase">
            <Play class="h-4 w-4" />
            {{ submitting ? t('caseDetail.running') : t('caseDetail.runAction') }}
          </UiButton>
        </div>
      </AppCard>

      <AppCard class="grid gap-4">
        <div class="grid gap-2">
          <h2 class="app-section-title">{{ t('caseDetail.optimizeTitle') }}</h2>
          <p class="app-section-description">{{ t('caseDetail.optimizeDescription') }}</p>
        </div>
        <AppEmptyState
          v-if="!latestOptimize"
          :title="t('caseDetail.optimizeEmptyTitle')"
          :description="t('caseDetail.optimizeEmptyDescription')"
        />
        <div v-else class="grid gap-4">
          <div class="flex flex-wrap items-start justify-between gap-3 rounded-xl border border-border-muted bg-surface-muted p-4">
            <div class="grid gap-2">
              <div class="flex flex-wrap items-center gap-2">
                <AppBadge :tone="optimizeTone(latestOptimize.status)">{{ t(`runs.status.${latestOptimize.status}`) }}</AppBadge>
                <time
                  v-if="latestOptimizeUpdatedAt"
                  :datetime="time.datetime(latestOptimizeUpdatedAt) ?? undefined"
                  :title="time.tooltip(latestOptimizeUpdatedAt) ?? undefined"
                  class="text-sm text-text-secondary"
                >
                  {{ t('caseDetail.optimizeUpdatedAt') }}: {{ time.relative(latestOptimizeUpdatedAt) }}
                </time>
              </div>
              <p v-if="latestOptimize.summary" class="text-sm text-text-primary">
                {{ t('caseDetail.optimizeSummary') }}: {{ latestOptimize.summary }}
              </p>
              <p v-if="latestOptimize.error_message" class="text-sm text-error-text">
                {{ t('caseDetail.optimizeError') }}: {{ latestOptimize.error_message }}
              </p>
              <p v-if="(latestOptimize.patched_fields ?? []).length > 0" class="text-sm text-text-secondary">
                {{ t('caseDetail.optimizePatchedFields') }}: {{ (latestOptimize.patched_fields ?? []).join(', ') }}
              </p>
            </div>
            <RouterLink class="secondary-link" :to="`/runs/${encodeURIComponent(latestOptimize.operation_id)}`">
              {{ t('caseDetail.optimizeOpenRun') }}
            </RouterLink>
          </div>
        </div>
      </AppCard>

      <AppCard class="grid gap-4">
        <div class="grid gap-2">
          <h2 class="app-section-title">{{ t('caseDetail.recentRunsTitle') }}</h2>
          <p class="app-section-description">{{ t('caseDetail.recentRunsDescription') }}</p>
        </div>
        <p v-if="recentRunsQuery.isFetching.value" class="text-sm text-text-secondary">{{ t('common.loading') }}</p>
        <AppEmptyState
          v-else-if="recentRuns.length === 0"
          :title="t('caseDetail.recentRunsEmptyTitle')"
          :description="t('caseDetail.recentRunsEmptyDescription')"
        />
        <div v-else class="grid gap-3">
          <article v-for="item in recentRuns" :key="item.operation_id" class="flex flex-wrap items-start justify-between gap-3 rounded-xl border border-border-muted bg-surface-muted p-4">
            <div class="grid gap-2">
              <RouterLink class="text-sm font-semibold text-text-primary transition-colors hover:text-accent" :to="`/runs/${encodeURIComponent(item.operation_id)}`">
                {{ item.title || item.target_label || item.operation_id }}
              </RouterLink>
              <div class="flex flex-wrap gap-x-3 gap-y-2 text-sm text-text-secondary">
                <span class="inline-flex items-center gap-1.5"><Smartphone class="h-3.5 w-3.5" />{{ deviceLabel(item.device_ref) }}</span>
                <time
                  :datetime="time.datetime(item.created_at) ?? undefined"
                  :title="time.tooltip(item.created_at)"
                >
                  {{ time.relative(item.created_at) }}
                </time>
              </div>
            </div>
            <AppBadge :tone="runTone(item)">{{ item.status }}</AppBadge>
          </article>
        </div>
      </AppCard>

      <CaseRewritePreviewModal
        :open="rewriteModalOpen"
        :prompt-value="rewritePrompt"
        :generating="rewriteCasePreviewMutation.isPending.value"
        :preview="rewritePreview"
        :error-message="rewriteError"
        @close="closeRewriteModal"
        @generate="handleGenerateRewritePreview"
        @apply="handleApplyRewritePreview"
        @update:prompt-value="rewritePrompt = $event"
      />
    </template>
  </section>
</template>
