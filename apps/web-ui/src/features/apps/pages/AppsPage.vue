<script setup lang="ts">
import { BookOpen, PlusCircle, RefreshCcw, SquarePen } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import AppCard from '@/shared/components/AppCard.vue'
import AppEmptyState from '@/shared/components/AppEmptyState.vue'
import UiButton from '@/shared/ui/UiButton.vue'
import { useAppsQuery } from '@/features/apps/queries/useAppsQuery'

type AppPlatform = 'android' | 'ios' | 'web'
type FilterPlatform = 'all' | AppPlatform

const router = useRouter()
const { t } = useI18n()

const platformFilter = ref<FilterPlatform>('all')

const appsQuery = useAppsQuery(computed(() => (
  platformFilter.value === 'all' ? {} : { platform: platformFilter.value }
)))

const apps = computed(() => appsQuery.data.value ?? [])
const listErrorMessage = computed(() => {
  const error = appsQuery.error.value
  if (!error) {
    return null
  }
  if (error instanceof Error) {
    return error.message
  }
  return String(error)
})

const platformFilterOptions = computed(() => [
  { value: 'all', label: t('apps.filters.all') },
  { value: 'android', label: t('apps.filters.android') },
  { value: 'ios', label: t('apps.filters.ios') },
  { value: 'web', label: t('apps.filters.web') },
])

async function handleCreate() {
  await router.push({ name: 'apps-create' })
}

async function handleSelect(appId: string) {
  await router.push({ name: 'apps-edit', params: { appId } })
}

async function handleOpenKnowledge(appId: string) {
  await router.push({ name: 'apps-knowledge', params: { appId } })
}

function displayAppName(item: { app_id: string } & Record<string, unknown>): string {
  return typeof item.app_name === 'string' && item.app_name.trim() ? item.app_name : item.app_id
}
</script>

<template>
  <section class="app-page grid gap-4">
    <AppCard class="flex flex-wrap items-center justify-between gap-3">
      <div class="flex flex-wrap gap-2">
        <button
          v-for="option in platformFilterOptions"
          :key="option.value"
          type="button"
          class="inline-flex min-h-8 items-center rounded-full border px-3 py-1 text-sm font-medium transition-all duration-150"
          :class="platformFilter === option.value ? 'border-accent bg-accent-soft text-accent' : 'border-border bg-surface-default text-text-secondary hover:border-border-strong hover:bg-surface-muted hover:text-text-primary'"
          @click="platformFilter = option.value as FilterPlatform"
        >
          {{ option.label }}
        </button>
      </div>
      <div class="flex flex-wrap gap-2">
        <UiButton type="button" variant="secondary" @click="() => void appsQuery.refetch()">
          <RefreshCcw class="h-4 w-4" />
          {{ t('common.refresh') }}
        </UiButton>
        <UiButton type="button" variant="primary" @click="handleCreate">
          <PlusCircle class="h-4 w-4" />
          {{ t('apps.actions.addApp') }}
        </UiButton>
      </div>
    </AppCard>

    <div class="grid gap-4">
      <div class="flex items-center justify-between gap-3">
        <div>
          <h2 class="text-base font-semibold text-text-primary">{{ t('apps.appsTitle') }}</h2>
        </div>
      </div>

      <AppEmptyState
        v-if="listErrorMessage"
        :title="t('apps.errorTitle')"
        :description="listErrorMessage"
      />

      <AppEmptyState
        v-else-if="!appsQuery.isFetching.value && apps.length === 0"
        :title="t('apps.emptyTitle')"
        :description="t('apps.emptyDescription')"
      />

      <div v-else class="grid gap-3">
        <article
          v-for="item in apps"
          :key="item.app_id"
          class="grid gap-3 rounded-xl border border-border-muted bg-surface-default px-4 py-4 text-left transition-colors hover:border-border-strong hover:bg-surface-muted"
        >
          <div class="flex items-center justify-between gap-3">
            <div class="min-w-0">
              <p class="font-medium text-text-primary">{{ displayAppName(item) }}</p>
              <p class="text-xs text-text-muted">{{ item.app_id }}</p>
            </div>
            <span class="rounded-full border border-border px-2 py-0.5 text-xs uppercase tracking-[0.12em] text-text-secondary">
              {{ item.platform }}
            </span>
          </div>
          <p class="text-sm text-text-secondary">{{ item.entry_identity || t('common.unavailable') }}</p>
          <div class="flex flex-wrap items-center justify-between gap-3">
            <p class="text-xs text-text-muted">
              {{ t('apps.usageSummary', { plans: item.plan_count, cases: item.case_count }) }}
            </p>
            <div class="flex flex-wrap items-center gap-2">
              <UiButton type="button" size="sm" variant="secondary" @click="handleSelect(item.app_id)">
                <SquarePen class="h-4 w-4" />
                {{ t('apps.actions.openApp') }}
              </UiButton>
              <UiButton type="button" size="sm" variant="ghost" @click="handleOpenKnowledge(item.app_id)">
                <BookOpen class="h-4 w-4" />
                {{ t('apps.actions.openKnowledge') }}
              </UiButton>
            </div>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>
