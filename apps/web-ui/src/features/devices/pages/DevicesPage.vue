<script setup lang="ts">
import { Cpu, RefreshCcw } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import AppBadge from '@/shared/components/AppBadge.vue'
import AppCard from '@/shared/components/AppCard.vue'
import AppEmptyState from '@/shared/components/AppEmptyState.vue'
import { LocalApiClientError } from '@/shared/api/client'
import type { DeviceDescriptor } from '@/shared/api/recording'
import { translateErrorCode } from '@/shared/i18n/errorMessages'
import { useDevicesQuery } from '@/features/devices/queries/useDevicesQuery'

const { t } = useI18n()

const selectedPlatform = ref('all')
const bootedOnly = ref(false)
const devicesQuery = useDevicesQuery(selectedPlatform)

const devices = computed(() => {
  const items = devicesQuery.data.value ?? []
  if (!bootedOnly.value) {
    return items
  }
  return items.filter((device) => device.is_booted === true)
})
const errorMessage = computed(() => {
  const error = devicesQuery.error.value
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

const platformOptions = computed(() => [
  { value: 'all', label: t('devices.filters.all') },
  { value: 'android', label: t('devices.filters.android') },
  { value: 'ios', label: t('devices.filters.ios') },
  { value: 'web', label: t('devices.filters.web') },
])

function toneForAvailability(value: string): 'neutral' | 'success' | 'error' | 'warning' {
  if (value === 'available') {
    return 'success'
  }
  if (value === 'busy') {
    return 'warning'
  }
  if (value === 'offline' || value === 'unsupported') {
    return 'error'
  }
  return 'neutral'
}

function bootState(device: DeviceDescriptor): string | null {
  if (device.is_booted == null) {
    return null
  }
  return device.is_booted ? t('devices.booted') : t('devices.notBooted')
}

function capabilitySummary(device: DeviceDescriptor): string {
  const raw = device.raw ?? {}
  const bits: string[] = []
  if (typeof raw.model === 'string' && raw.model.trim()) {
    bits.push(raw.model)
  }
  if (typeof raw.runtime_id === 'string' && raw.runtime_id.trim()) {
    bits.push(raw.runtime_id)
  }
  if (typeof raw.os_version === 'string' && raw.os_version.trim()) {
    bits.push(raw.os_version)
  }
  return bits.join(' / ') || t('devices.capabilityUnknown')
}
</script>

<template>
  <section class="app-page">
    <AppCard>
      <div class="app-toolbar">
        <div class="flex flex-wrap items-center gap-2">
          <div class="flex flex-wrap gap-2">
            <button
              v-for="option in platformOptions"
              :key="option.value"
              type="button"
              class="inline-flex min-h-8 items-center rounded-full border px-3 py-1 text-sm font-medium transition-all duration-150"
              :class="selectedPlatform === option.value ? 'border-accent bg-accent-soft text-accent' : 'border-border bg-surface-default text-text-secondary hover:border-border-strong hover:bg-surface-muted hover:text-text-primary'"
              @click="selectedPlatform = option.value"
            >
              {{ option.label }}
            </button>
          </div>
          <label class="inline-flex min-h-9 items-center gap-2 rounded-full border border-border bg-surface-default px-3 text-sm text-text-secondary transition-colors hover:border-border-strong hover:bg-surface-muted hover:text-text-primary">
            <input v-model="bootedOnly" type="checkbox" class="h-4 w-4 rounded border-border">
            {{ t('devices.filters.bootedOnly') }}
          </label>
        </div>
        <button type="button" class="inline-flex min-h-9 items-center gap-2 rounded-md border border-border bg-surface-default px-3 text-sm font-medium text-text-primary transition-colors hover:border-border-strong hover:bg-surface-muted" @click="() => void devicesQuery.refetch()">
          <RefreshCcw class="h-4 w-4 text-text-secondary" />
          {{ t('common.refresh') }}
        </button>
      </div>
    </AppCard>

    <AppCard v-if="devicesQuery.isFetching.value">
      <p class="muted">{{ t('common.loading') }}</p>
    </AppCard>

    <AppEmptyState
      v-else-if="errorMessage"
      :title="t('devices.errorTitle')"
      :description="errorMessage"
    />

    <AppEmptyState
      v-else-if="devices.length === 0"
      :title="t('devices.emptyTitle')"
      :description="bootedOnly ? t('devices.emptyFilteredDescription') : t('devices.emptyDescription')"
    />

    <div v-else class="grid gap-3">
      <article v-for="device in devices" :key="device.device_ref" class="grid gap-4 rounded-lg border border-border-muted bg-surface-default p-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-start">
        <div class="grid gap-3">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div class="inline-flex items-center gap-2">
                <Cpu class="h-4 w-4 text-text-muted" />
                <h2 class="text-base font-semibold text-text-primary">{{ device.display_name }}</h2>
              </div>
              <p class="mt-1 text-sm text-text-secondary">{{ device.device_ref }}</p>
            </div>
            <AppBadge :tone="toneForAvailability(device.availability)">{{ device.availability }}</AppBadge>
          </div>
          <div class="flex flex-wrap gap-x-3 gap-y-2 text-sm text-text-secondary">
            <span>{{ device.platform }}</span>
            <span>{{ device.kind }}</span>
            <span v-if="bootState(device)">{{ bootState(device) }}</span>
          </div>
          <p class="text-sm leading-6 text-text-secondary">{{ capabilitySummary(device) }}</p>
        </div>
        <div class="grid gap-2 sm:grid-cols-2 lg:grid-cols-1">
          <RouterLink class="inline-flex min-h-9 items-center justify-center rounded-md border border-border bg-surface-default px-3 text-sm font-medium text-text-primary transition-colors hover:border-border-strong hover:bg-surface-muted" to="/recording">{{ t('devices.actions.recording') }}</RouterLink>
          <RouterLink class="inline-flex min-h-9 items-center justify-center rounded-md border border-border bg-surface-default px-3 text-sm font-medium text-text-primary transition-colors hover:border-border-strong hover:bg-surface-muted" to="/runs">{{ t('devices.actions.runs') }}</RouterLink>
        </div>
      </article>
    </div>
  </section>
</template>
