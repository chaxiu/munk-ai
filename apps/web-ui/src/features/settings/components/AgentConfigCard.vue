<script setup lang="ts">
import { ChevronDown } from '@lucide/vue'
import { computed, ref, toRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import AppCard from '@/shared/components/AppCard.vue'
import UiField from '@/shared/ui/UiField.vue'
import UiSelect from '@/shared/ui/UiSelect.vue'
import ProviderSectionForm from './ProviderSectionForm.vue'
import type { AgentForm, ProviderKind } from '../types'

const props = defineProps<{
  role: string
  roleLabel: string
  config: AgentForm
}>()

const { t } = useI18n()
const isExpanded = ref(false)
const config = toRef(props, 'config')

const providerOptions = computed(() => [
  { value: 'openai_compatible', label: t('settings.providers.openaiCompatible') },
  { value: 'gemini', label: t('settings.providers.gemini') },
])

const providerLabel = computed(() => {
  if (config.value.provider === 'openai_compatible') {
    return t('settings.providers.openaiCompatible')
  }
  if (config.value.provider === 'gemini') {
    return t('settings.providers.gemini')
  }
  return ''
})

const summaryText = computed(() => {
  if (!config.value.enabled) {
    return t('settings.agent.inheritDescription')
  }
  if (!config.value.provider) {
    return t('settings.agent.missingProviderSummary')
  }
  return t('settings.agent.overrideSummary', { provider: providerLabel.value })
})

watch(() => config.value.enabled, (enabled) => {
  if (!enabled) {
    config.value.provider = ''
    isExpanded.value = false
    return
  }
})

watch(() => config.value.provider, (provider) => {
  if (provider === 'openai_compatible') {
    config.value.openai_compatible.configured = true
  }
  if (provider === 'gemini') {
    config.value.gemini.configured = true
  }
})

function isActive(kind: ProviderKind): boolean {
  return config.value.enabled && config.value.provider === kind
}
</script>

<template>
  <AppCard class="px-4 py-4 md:px-5">
    <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
      <div class="min-w-0 flex-1">
        <div class="flex flex-wrap items-center gap-2.5">
          <h3 class="text-base font-semibold text-text-primary">{{ roleLabel }}</h3>
          <span
            class="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium"
            :class="config.enabled ? 'bg-accent/12 text-accent' : 'bg-surface-muted text-text-secondary'"
          >
            {{ config.enabled ? t('settings.agent.enabledState') : t('settings.agent.inheritState') }}
          </span>
          <span v-if="config.enabled && providerLabel" class="text-xs font-medium text-text-muted">
            {{ providerLabel }}
          </span>
        </div>
        <p class="mt-1 text-sm text-text-secondary">{{ summaryText }}</p>
      </div>

      <div class="flex shrink-0 items-center gap-3">
        <label class="inline-flex min-h-11 items-center gap-2 rounded-xl border border-border bg-surface-muted/30 px-3.5 text-sm text-text-secondary">
          <input v-model="config.enabled" type="checkbox" class="h-4 w-4 rounded border-border">
          {{ t('settings.agent.enableOverride') }}
        </label>
        <button
          v-if="config.enabled"
          type="button"
          class="inline-flex min-h-11 items-center gap-2 rounded-xl px-3 text-xs font-medium text-text-muted transition-colors duration-150 hover:bg-surface-muted/35 hover:text-text-primary"
          @click="isExpanded = !isExpanded"
        >
          <span>{{ isExpanded ? t('settings.agent.hideDetails') : t('settings.agent.showDetails') }}</span>
          <ChevronDown class="h-4 w-4 transition-transform duration-150" :class="isExpanded ? 'rotate-180' : ''" />
        </button>
      </div>
    </div>

    <template v-if="config.enabled && isExpanded">
      <div class="mt-4 grid gap-4 border-t border-border pt-4">
        <div class="max-w-sm">
          <UiField :label="t('settings.fields.provider')">
            <UiSelect
              v-model="config.provider"
              :options="providerOptions"
              :placeholder="t('settings.placeholders.selectProvider')"
            />
          </UiField>
        </div>

        <div class="divide-y divide-border rounded-xl border border-border bg-surface-default/35">
          <ProviderSectionForm
            kind="openai_compatible"
            :section="config.openai_compatible"
            :active="isActive('openai_compatible')"
            :default-expanded="false"
          />
          <ProviderSectionForm
            kind="gemini"
            :section="config.gemini"
            :active="isActive('gemini')"
            :default-expanded="false"
          />
        </div>
      </div>
    </template>
  </AppCard>
</template>
