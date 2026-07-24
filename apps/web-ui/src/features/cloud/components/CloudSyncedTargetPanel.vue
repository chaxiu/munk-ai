<script setup lang="ts">
import { ArrowDownToLine, ArrowUpFromLine, CheckCircle2, Unlink } from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import type { CloudLinkItemData, CloudSyncStatusData } from '@/shared/api/cloudSync'
import UiButton from '@/shared/ui/UiButton.vue'

const props = defineProps<{
  links: CloudLinkItemData[]
  activeAppId: string | null
  status: CloudSyncStatusData | null
  statusLoading: boolean
  statusError: string | null
  busy: boolean
  pulling: boolean
  pushing: boolean
  unlinkingAppId: string | null
  settingActiveAppId: string | null
}>()

const emit = defineEmits<{
  pull: []
  push: []
  setActive: [appId: string]
  unlink: [appId: string]
}>()

const { t } = useI18n()

const activeLink = computed(() => (
  props.links.find((item) => item.app_id === props.activeAppId) ?? props.links[0] ?? null
))
const canPull = computed(() => Boolean(props.status?.can_pull))
const canPush = computed(() => Boolean(props.status?.can_push))

const showNotYetSyncedHint = computed(() => {
  if (!activeLink.value) {
    return false
  }
  if (!props.status) {
    return true
  }
  return !props.status.last_action
})

const hasLinks = computed(() => props.links.length > 0)

function formatTimestamp(value: string | null | undefined): string {
  if (!value) {
    return '—'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString()
}
</script>

<template>
  <section class="grid gap-3">
    <div class="grid gap-1">
      <h3 class="text-sm font-medium text-text-primary">{{ t('cloud.sync.linkedAppsTitle') }}</h3>
      <p class="text-sm text-text-secondary">{{ t('cloud.sync.linkedAppsHint') }}</p>
    </div>

    <p v-if="!hasLinks" class="rounded-lg border border-dashed border-border-muted px-3 py-3 text-sm text-text-secondary">
      {{ t('cloud.sync.emptyLinks') }}
    </p>
    <div v-else class="grid gap-2">
      <div
        v-for="link in links"
        :key="link.app_id"
        class="grid gap-3 rounded-lg border px-3 py-3 text-sm transition-colors"
        :class="link.app_id === activeLink?.app_id ? 'border-accent bg-accent-soft/40' : 'border-border-muted bg-surface-default'"
      >
        <div class="flex flex-wrap items-start justify-between gap-3">
          <button
            type="button"
            class="min-w-0 flex-1 text-left"
            :disabled="busy || link.app_id === activeLink?.app_id"
            @click="emit('setActive', link.app_id)"
          >
            <span class="flex flex-wrap items-center gap-2">
              <span class="font-medium text-text-primary">{{ link.app_id }}</span>
              <span
                v-if="link.app_id === activeLink?.app_id"
                class="inline-flex items-center gap-1 rounded-full bg-accent px-2 py-0.5 text-xs font-medium text-white"
              >
                <CheckCircle2 class="h-3 w-3" />
                {{ t('cloud.sync.currentApp') }}
              </span>
              <span
                v-else
                class="rounded-full border border-border px-2 py-0.5 text-xs text-text-secondary"
              >
                {{ settingActiveAppId === link.app_id ? t('cloud.sync.settingCurrent') : t('cloud.sync.setCurrent') }}
              </span>
              <span
                v-if="link.dirty"
                class="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800"
              >
                {{ t('cloud.sync.dirty') }}
              </span>
            </span>
            <span class="mt-1 block text-xs text-text-secondary">
              {{ link.workspace_name || link.workspace_id }} · {{ link.role || '—' }}
            </span>
          </button>

          <UiButton
            type="button"
            size="sm"
            variant="secondary"
            :disabled="busy"
            @click="emit('unlink', link.app_id)"
          >
            <Unlink class="h-4 w-4" />
            {{ unlinkingAppId === link.app_id ? t('cloud.sync.unlinking') : t('cloud.sync.unlink') }}
          </UiButton>
        </div>

        <div class="grid gap-1 text-xs text-text-secondary sm:grid-cols-3">
          <span>{{ t('cloud.sync.baseRevision') }}: {{ link.base_revision ?? '—' }}</span>
          <span>{{ t('cloud.sync.lastSyncedAt') }}: {{ formatTimestamp(link.last_synced_at) }}</span>
          <span>{{ t('cloud.sync.lastAction') }}: {{ link.last_action ?? '—' }}</span>
        </div>
      </div>
    </div>

    <template v-if="activeLink">
      <p v-if="statusLoading && !status" class="text-sm text-text-secondary">
        {{ t('common.loading') }}
      </p>
      <div
        v-else-if="statusError"
        class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
      >
        {{ statusError }}
      </div>
      <div v-else class="grid gap-2 rounded-lg border border-border-muted px-3 py-3 text-sm">
        <div class="flex flex-wrap justify-between gap-2">
          <span class="text-text-secondary">{{ t('cloud.sync.activeApp') }}</span>
          <span class="font-medium text-text-primary">{{ activeLink.app_id }}</span>
        </div>
        <div class="flex flex-wrap justify-between gap-2">
          <span class="text-text-secondary">{{ t('cloud.sync.cloudRevision') }}</span>
          <span class="font-medium text-text-primary">{{ status?.revision ?? '—' }}</span>
        </div>
        <div class="flex flex-wrap justify-between gap-2">
          <span class="text-text-secondary">{{ t('cloud.sync.baseRevision') }}</span>
          <span class="font-medium text-text-primary">{{ status?.base_revision ?? activeLink.base_revision ?? '—' }}</span>
        </div>
        <div class="flex flex-wrap justify-between gap-2">
          <span class="text-text-secondary">{{ t('cloud.sync.dirty') }}</span>
          <span class="font-medium text-text-primary">
            {{ (status?.dirty ?? activeLink.dirty) ? t('cloud.sync.dirtyYes') : t('cloud.sync.dirtyNo') }}
          </span>
        </div>
        <div class="flex flex-wrap justify-between gap-2">
          <span class="text-text-secondary">{{ t('cloud.sync.lastSyncedAt') }}</span>
          <span class="font-medium text-text-primary">{{ formatTimestamp(status?.last_synced_at ?? activeLink.last_synced_at) }}</span>
        </div>
        <div class="flex flex-wrap justify-between gap-2">
          <span class="text-text-secondary">{{ t('cloud.sync.lastAction') }}</span>
          <span class="font-medium text-text-primary">{{ status?.last_action ?? activeLink.last_action ?? '—' }}</span>
        </div>
      </div>

      <p v-if="showNotYetSyncedHint" class="text-sm text-text-secondary">
        {{ t('cloud.sync.notYetSyncedHint') }}
      </p>

      <div class="flex flex-wrap items-center gap-2">
        <UiButton
          type="button"
          variant="primary"
          :disabled="busy || !canPull"
          @click="emit('pull')"
        >
          <ArrowDownToLine class="h-4 w-4" />
          {{ pulling ? t('cloud.sync.pulling') : t('cloud.sync.pull') }}
        </UiButton>
        <UiButton
          type="button"
          variant="secondary"
          :disabled="busy || !canPush"
          @click="emit('push')"
        >
          <ArrowUpFromLine class="h-4 w-4" />
          {{ pushing ? t('cloud.sync.pushing') : t('cloud.sync.push') }}
        </UiButton>
      </div>
      <p v-if="status && !canPush" class="text-sm text-text-secondary">
        {{ t('cloud.sync.pushDisabledHint') }}
      </p>
    </template>
  </section>
</template>
