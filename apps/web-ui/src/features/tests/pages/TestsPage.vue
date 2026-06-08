<script setup lang="ts">
import { RefreshCcw, Search } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import AppBadge from '@/shared/components/AppBadge.vue'
import AppEmptyState from '@/shared/components/AppEmptyState.vue'
import UiButton from '@/shared/ui/UiButton.vue'
import UiInput from '@/shared/ui/UiInput.vue'
import UiSelect from '@/shared/ui/UiSelect.vue'
import { LocalApiClientError } from '@/shared/api/client'
import { translateErrorCode } from '@/shared/i18n/errorMessages'
import { useTime } from '@/shared/time/useTime'
import { useCaseSearchQuery } from '@/features/tests/queries/useCaseSearchQuery'
import { usePlansQuery } from '@/features/tests/queries/usePlansQuery'
import { formatPlanSourceLabel } from '@/features/tests/sourceLabels'
import { formatStartModeLabel } from '@/features/tests/startModeLabels'
import { formatVerdictLabel } from '@/features/runs/lib/runMappers'

const { t } = useI18n()
const time = useTime({ relative: true })
const PAGE_SIZE = 20

const appIdFilter = ref('')
const sourceFilter = ref('all')
const caseCountFilter = ref<'all' | 'single' | 'multi'>('all')
const viewMode = ref<'plans' | 'search'>('plans')
const plansPage = ref(1)
const searchPage = ref(1)
const searchQuery = ref('')
const searchAppId = ref('')
const searchPlanId = ref('')
const searchCaseId = ref('')
const searchIsCoreCase = ref<'all' | 'true' | 'false'>('all')
const searchStartMode = ref<'all' | 'reset' | 'resume'>('all')

const plansOffset = computed(() => (plansPage.value - 1) * PAGE_SIZE)
const searchOffset = computed(() => (searchPage.value - 1) * PAGE_SIZE)
const caseSearchEnabled = computed(() => Boolean(
  searchQuery.value.trim()
  || searchAppId.value.trim()
  || searchPlanId.value.trim()
  || searchCaseId.value.trim()
  || searchIsCoreCase.value !== 'all'
  || searchStartMode.value !== 'all'
))

const plansQuery = usePlansQuery(computed(() => ({
  appId: appIdFilter.value.trim() || undefined,
  source: sourceFilter.value === 'all' ? undefined : sourceFilter.value,
  caseCountMode: caseCountFilter.value,
  includeLatestRun: true,
  limit: PAGE_SIZE,
  offset: plansOffset.value,
})))

const caseSearchQuery = useCaseSearchQuery(computed(() => ({
  query: searchQuery.value.trim() || undefined,
  appId: searchAppId.value.trim() || undefined,
  planId: searchPlanId.value.trim() || undefined,
  caseId: searchCaseId.value.trim() || undefined,
  isCoreCase: searchIsCoreCase.value === 'all' ? undefined : searchIsCoreCase.value === 'true',
  startMode: searchStartMode.value === 'all' ? undefined : searchStartMode.value,
  limit: PAGE_SIZE,
  offset: searchOffset.value,
})))

const plans = computed(() => plansQuery.data.value?.items ?? [])
const plansTotal = computed(() => plansQuery.data.value?.total ?? 0)
const plansTotalPages = computed(() => Math.max(1, Math.ceil(plansTotal.value / PAGE_SIZE)))
const hasPreviousPlansPage = computed(() => plansPage.value > 1)
const hasNextPlansPage = computed(() => plansPage.value < plansTotalPages.value)

const searchResults = computed(() => caseSearchQuery.data.value?.items ?? [])
const searchTotal = computed(() => caseSearchQuery.data.value?.total ?? 0)
const searchTotalPages = computed(() => Math.max(1, Math.ceil(searchTotal.value / PAGE_SIZE)))
const hasPreviousSearchPage = computed(() => searchPage.value > 1)
const hasNextSearchPage = computed(() => searchPage.value < searchTotalPages.value)

const planErrorMessage = computed(() => {
  const error = plansQuery.error.value
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

const searchErrorMessage = computed(() => {
  const error = caseSearchQuery.error.value
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

watch([appIdFilter, sourceFilter, caseCountFilter], () => {
  plansPage.value = 1
})

watch([searchQuery, searchAppId, searchPlanId, searchCaseId, searchIsCoreCase, searchStartMode], () => {
  searchPage.value = 1
})

function sourceTone(source: string): 'neutral' | 'warning' | 'success' {
  if (source === 'change_verification') {
    return 'warning'
  }
  if (source === 'pydantic_plan_agent' || source === 'recording_export') {
    return 'success'
  }
  if (source === 'plan_import') {
    return 'success'
  }
  return 'neutral'
}

function latestRunStatusTone(status?: string | null): 'neutral' | 'success' | 'error' | 'warning' {
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

function latestRunVerdictTone(verdict?: string | null): 'neutral' | 'success' | 'error' | 'warning' {
  if (verdict === 'passed') {
    return 'success'
  }
  if (verdict === 'failed') {
    return 'error'
  }
  if (verdict === 'inconclusive') {
    return 'warning'
  }
  return 'neutral'
}

function refreshCurrent() {
  if (viewMode.value === 'plans') {
    void plansQuery.refetch()
    return
  }
  if (caseSearchEnabled.value) {
    void caseSearchQuery.refetch()
  }
}

const sourceOptions = computed(() => [
  { value: 'all', label: t('tests.filters.allSources') },
  { value: 'pydantic_plan_agent', label: formatPlanSourceLabel('pydantic_plan_agent', t) },
  { value: 'change_verification', label: formatPlanSourceLabel('change_verification', t) },
  { value: 'change_driven_plan_agent', label: formatPlanSourceLabel('change_driven_plan_agent', t) },
  { value: 'recording_export', label: formatPlanSourceLabel('recording_export', t) },
  { value: 'plan_import', label: formatPlanSourceLabel('plan_import', t) },
])

const caseCountOptions = computed(() => [
  { value: 'all', label: t('tests.filters.allCaseCounts') },
  { value: 'single', label: t('tests.filters.singleCase') },
  { value: 'multi', label: t('tests.filters.multiCase') },
])

const startModeOptions = computed(() => [
  { value: 'all', label: t('tests.search.allStartModes') },
  { value: 'reset', label: formatStartModeLabel('reset', t) },
  { value: 'resume', label: formatStartModeLabel('resume', t) },
])

function displayPlanName(planName?: string | null, planId?: string | null): string {
  return planName?.trim() || planId?.trim() || ''
}

function goToPreviousPlansPage() {
  if (hasPreviousPlansPage.value) {
    plansPage.value -= 1
  }
}

function goToNextPlansPage() {
  if (hasNextPlansPage.value) {
    plansPage.value += 1
  }
}

function goToPreviousSearchPage() {
  if (hasPreviousSearchPage.value) {
    searchPage.value -= 1
  }
}

function goToNextSearchPage() {
  if (hasNextSearchPage.value) {
    searchPage.value += 1
  }
}
</script>

<template>
  <section class="app-page">
    <div class="grid gap-4">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="inline-flex rounded-lg border border-border bg-surface-default p-1">
          <button
            type="button"
            class="inline-flex min-h-9 items-center rounded-md px-3 text-sm font-medium transition-colors"
            :class="viewMode === 'plans' ? 'bg-accent text-white shadow-sm' : 'text-text-secondary hover:bg-surface-muted hover:text-text-primary'"
            @click="viewMode = 'plans'"
          >
            {{ t('tests.plans.title') }}
          </button>
          <button
            type="button"
            class="inline-flex min-h-9 items-center rounded-md px-3 text-sm font-medium transition-colors"
            :class="viewMode === 'search' ? 'bg-accent text-white shadow-sm' : 'text-text-secondary hover:bg-surface-muted hover:text-text-primary'"
            @click="viewMode = 'search'"
          >
            {{ t('tests.search.title') }}
          </button>
        </div>
        <button type="button" class="inline-flex min-h-9 items-center gap-2 rounded-md border border-border bg-surface-default px-3 text-sm font-medium text-text-primary transition-colors hover:border-border-strong hover:bg-surface-muted" @click="refreshCurrent">
          <RefreshCcw class="h-4 w-4 text-text-secondary" />
          {{ t('common.refresh') }}
        </button>
      </div>

      <template v-if="viewMode === 'plans'">
        <div class="grid gap-3 md:grid-cols-3">
          <UiInput v-model="appIdFilter" :placeholder="t('tests.filters.appIdPlaceholder')" />
          <UiSelect v-model="sourceFilter" :options="sourceOptions" :placeholder="t('tests.filters.allSources')" />
          <UiSelect v-model="caseCountFilter" :options="caseCountOptions" :placeholder="t('tests.filters.allCaseCounts')" />
        </div>

        <p v-if="plansQuery.isFetching.value" class="text-sm text-text-secondary">{{ t('common.loading') }}</p>
        <AppEmptyState
          v-else-if="planErrorMessage"
          :title="t('tests.plans.errorTitle')"
          :description="planErrorMessage"
        />
        <AppEmptyState
          v-else-if="plans.length === 0"
          :title="t('tests.plans.emptyTitle')"
          :description="t('tests.plans.emptyDescription')"
        />
        <div v-else class="grid gap-3">
          <article v-for="plan in plans" :key="`${plan.app_id}:${plan.plan_id}`" class="grid gap-2 rounded-lg border border-border-muted bg-surface-default p-3">
            <div class="grid gap-2">
              <div class="flex flex-wrap items-start justify-between gap-3">
                <div class="flex flex-wrap items-center gap-2">
                  <RouterLink
                    class="text-sm font-semibold text-text-primary transition-colors hover:text-accent"
                    :to="`/tests/plans/${encodeURIComponent(plan.app_id)}/${encodeURIComponent(plan.plan_id)}`"
                  >
                    {{ displayPlanName(plan.plan_name, plan.plan_id) }}
                  </RouterLink>
                  <AppBadge v-if="plan.case_count === 1" tone="warning">
                    {{ t('tests.plans.singleCasePlan') }}
                  </AppBadge>
                </div>
                <AppBadge :tone="sourceTone(plan.source)">{{ formatPlanSourceLabel(plan.source, t) }}</AppBadge>
              </div>
              <div class="flex flex-wrap gap-x-3 gap-y-2 text-sm text-text-secondary">
                <span>{{ plan.app_id }}</span>
                <span>{{ t('tests.plans.caseCount', { count: plan.case_count }) }}</span>
                <time
                  :datetime="time.datetime(plan.updated_at) ?? undefined"
                  :title="time.tooltip(plan.updated_at)"
                >
                  {{ time.relative(plan.updated_at) }}
                </time>
              </div>
            </div>
            <div
              v-if="plan.latest_run"
              class="flex flex-wrap items-start justify-between gap-3 border-t border-border-muted pt-3"
            >
              <div class="grid gap-2">
                <p class="text-xs font-semibold uppercase tracking-[0.12em] text-text-tertiary">
                  {{ t('tests.plans.latestRun.title') }}
                </p>
                <div class="flex flex-wrap items-center gap-2">
                  <AppBadge :tone="latestRunStatusTone(plan.latest_run.status)">
                    {{ `${t('tests.plans.latestRun.statusLabel')}: ${plan.latest_run.status}` }}
                  </AppBadge>
                  <AppBadge
                    v-if="plan.latest_run.verification_verdict"
                    :tone="latestRunVerdictTone(plan.latest_run.verification_verdict)"
                  >
                    {{ `${t('tests.plans.latestRun.verdictLabel')}: ${formatVerdictLabel(plan.latest_run.verification_verdict, t)}` }}
                  </AppBadge>
                </div>
              </div>
              <div class="flex flex-wrap items-center justify-end gap-x-3 gap-y-2 text-sm text-text-secondary">
                <time
                  :datetime="time.datetime(plan.latest_run.finished_at ?? plan.latest_run.started_at ?? plan.latest_run.created_at) ?? undefined"
                  :title="time.tooltip(plan.latest_run.finished_at ?? plan.latest_run.started_at ?? plan.latest_run.created_at)"
                >
                  {{ time.relative(plan.latest_run.finished_at ?? plan.latest_run.started_at ?? plan.latest_run.created_at) }}
                </time>
                <RouterLink
                  class="font-medium text-accent transition-colors hover:text-accent-strong"
                  :to="`/runs/${encodeURIComponent(plan.latest_run.operation_id)}`"
                >
                  {{ t('tests.plans.latestRun.openRun') }}
                </RouterLink>
              </div>
            </div>
          </article>
          <div class="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border-muted bg-surface-default px-4 py-3">
            <p class="text-sm text-text-secondary">
              {{ t('tests.pagination.summary', { page: plansPage, totalPages: plansTotalPages, total: plansTotal }) }}
            </p>
            <div class="flex items-center gap-2">
              <UiButton variant="secondary" size="sm" :disabled="!hasPreviousPlansPage" @click="goToPreviousPlansPage">
                {{ t('tests.pagination.previous') }}
              </UiButton>
              <UiButton variant="secondary" size="sm" :disabled="!hasNextPlansPage" @click="goToNextPlansPage">
                {{ t('tests.pagination.next') }}
              </UiButton>
            </div>
          </div>
        </div>
      </template>

      <template v-else>
        <div class="grid gap-3 md:grid-cols-3">
          <div class="relative md:col-span-3">
            <Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
            <UiInput v-model="searchQuery" :placeholder="t('tests.search.queryPlaceholder')" class="pl-10" />
          </div>
          <div class="relative">
            <Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
            <UiInput v-model="searchAppId" :placeholder="t('tests.search.appIdPlaceholder')" class="pl-10" />
          </div>
          <div class="relative">
            <Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
            <UiInput v-model="searchPlanId" :placeholder="t('tests.search.planIdPlaceholder')" class="pl-10" />
          </div>
          <div class="relative">
            <Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
            <UiInput v-model="searchCaseId" :placeholder="t('tests.search.caseIdPlaceholder')" class="pl-10" />
          </div>
          <UiSelect
            v-model="searchIsCoreCase"
            :options="[
              { value: 'all', label: t('tests.search.allCoreCases') },
              { value: 'true', label: t('tests.search.coreOnly') },
              { value: 'false', label: t('tests.search.nonCoreOnly') },
            ]"
            :placeholder="t('tests.search.allCoreCases')"
          />
          <UiSelect
            v-model="searchStartMode"
            :options="startModeOptions"
            :placeholder="t('tests.search.allStartModes')"
          />
        </div>

        <p v-if="caseSearchQuery.isFetching.value" class="text-sm text-text-secondary">{{ t('common.loading') }}</p>
        <AppEmptyState
          v-else-if="searchErrorMessage"
          :title="t('tests.search.errorTitle')"
          :description="searchErrorMessage"
        />
        <AppEmptyState
          v-else-if="!caseSearchEnabled"
          :title="t('tests.search.idleTitle')"
          :description="t('tests.search.idleDescription')"
        />
        <AppEmptyState
          v-else-if="searchResults.length === 0"
          :title="t('tests.search.emptyTitle')"
          :description="t('tests.search.emptyDescription')"
        />
        <div v-else class="grid gap-3">
          <article
            v-for="item in searchResults"
            :key="`${item.app_id}:${item.plan_id}:${item.case_id}`"
            class="grid gap-2 rounded-lg border border-border-muted bg-surface-default p-3"
          >
            <div class="grid gap-2">
              <div class="flex flex-wrap items-center gap-2">
                <RouterLink
                  class="text-sm font-semibold text-text-primary transition-colors hover:text-accent"
                  :to="`/tests/plans/${encodeURIComponent(item.app_id)}/${encodeURIComponent(item.plan_id)}/cases/${encodeURIComponent(item.case_id)}`"
                >
                  {{ item.case_id }}
                </RouterLink>
                <AppBadge v-if="item.is_core_case" tone="warning">
                  {{ t('planDetail.coreCase') }}
                </AppBadge>
              </div>
              <p class="text-sm text-text-primary">{{ item.title }}</p>
              <div class="flex flex-wrap gap-x-3 gap-y-2 text-sm text-text-secondary">
                <span>{{ item.app_id }}</span>
                <span>{{ displayPlanName(item.plan_name, item.plan_id) }}</span>
                <span>{{ formatStartModeLabel(item.start_mode, t) }}</span>
              </div>
            </div>
          </article>
          <div class="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border-muted bg-surface-default px-4 py-3">
            <p class="text-sm text-text-secondary">
              {{ t('tests.pagination.summary', { page: searchPage, totalPages: searchTotalPages, total: searchTotal }) }}
            </p>
            <div class="flex items-center gap-2">
              <UiButton variant="secondary" size="sm" :disabled="!hasPreviousSearchPage" @click="goToPreviousSearchPage">
                {{ t('tests.pagination.previous') }}
              </UiButton>
              <UiButton variant="secondary" size="sm" :disabled="!hasNextSearchPage" @click="goToNextSearchPage">
                {{ t('tests.pagination.next') }}
              </UiButton>
            </div>
          </div>
        </div>
      </template>
    </div>
  </section>
</template>
