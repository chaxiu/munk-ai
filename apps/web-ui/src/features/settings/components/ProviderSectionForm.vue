<script setup lang="ts">
import { ChevronDown } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import UiField from '@/shared/ui/UiField.vue'
import UiInput from '@/shared/ui/UiInput.vue'
import UiSelect from '@/shared/ui/UiSelect.vue'
import UiTextarea from '@/shared/ui/UiTextarea.vue'
import type { GeminiSectionForm, OpenAISectionForm, ProviderKind } from '../types'

const props = defineProps<{
  kind: ProviderKind
  section: OpenAISectionForm | GeminiSectionForm
  active: boolean
  defaultExpanded?: boolean
}>()

const { t } = useI18n()
const isExpanded = ref(Boolean(props.defaultExpanded))
const showGeminiAdvanced = ref(false)

const openaiSection = computed(() => props.section as OpenAISectionForm)
const geminiSection = computed(() => props.section as GeminiSectionForm)
const apiKeyHint = computed(() => (
  props.section.api_key_configured
    ? t('settings.fields.apiKeyConfigured')
    : t('settings.fields.optional')
))
const providerTitle = computed(() => (
  props.kind === 'openai_compatible'
    ? t('settings.providers.openaiCompatible')
    : t('settings.providers.gemini')
))
const outputStrategyOptions = computed(() => [
  { value: 'auto', label: t('settings.outputStrategy.auto') },
  { value: 'prompted', label: t('settings.outputStrategy.prompted') },
])
const thinkingModeOptions = computed(() => [
  { value: 'default', label: t('settings.thinkingMode.default') },
  { value: 'enabled', label: t('settings.thinkingMode.enabled') },
  { value: 'disabled', label: t('settings.thinkingMode.disabled') },
])
const summaryText = computed(() => {
  const details: string[] = []

  if (props.section.configured) {
    details.push(t('settings.providerCard.persisted'))
  } else {
    details.push(t('settings.providerCard.notPersisted'))
  }

  if (props.kind === 'openai_compatible') {
    if (openaiSection.value.model.trim()) {
      details.push(openaiSection.value.model.trim())
    }
    if (openaiSection.value.base_url.trim()) {
      details.push(openaiSection.value.base_url.trim())
    }
    details.push(t(`settings.outputStrategySummary.${openaiSection.value.output_strategy}`))
    details.push(t(`settings.thinkingModeSummary.${openaiSection.value.thinking_mode}`))
  } else {
    if (geminiSection.value.model.trim()) {
      details.push(geminiSection.value.model.trim())
    }
    if (props.section.api_key_configured) {
      details.push(t('settings.providerCard.apiKeyReady'))
    }
  }

  return details.join(' · ')
})

</script>

<template>
  <section class="px-4 py-3.5 transition-all duration-150 md:px-5">
    <button
      type="button"
      class="flex w-full items-start justify-between gap-4 text-left transition-colors duration-150"
      @click="isExpanded = !isExpanded"
    >
      <div class="min-w-0 grid flex-1 gap-2">
        <div class="flex flex-wrap items-center gap-2.5">
          <h3 class="text-sm font-semibold text-text-primary">{{ providerTitle }}</h3>
          <span
            class="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium"
            :class="active ? 'bg-accent/12 text-accent' : 'bg-surface-muted text-text-secondary'"
          >
            {{ active ? t('settings.providerCard.activeBadge') : t('settings.providerCard.standbyBadge') }}
          </span>
          <span
            class="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium"
            :class="section.configured ? 'bg-surface-muted text-text-primary' : 'bg-surface-muted text-text-muted'"
          >
            {{ section.configured ? t('settings.providerCard.persisted') : t('settings.providerCard.notPersisted') }}
          </span>
        </div>
        <p class="text-sm text-text-secondary">
          {{ summaryText || t('settings.providerCard.emptySummary') }}
        </p>
      </div>

      <div class="flex shrink-0 items-center gap-2 text-xs font-medium text-text-muted">
        <span>{{ isExpanded ? t('settings.providerCard.collapse') : t('settings.providerCard.expand') }}</span>
        <ChevronDown class="h-4 w-4 transition-transform duration-150" :class="isExpanded ? 'rotate-180' : ''" />
      </div>
    </button>

    <div v-if="isExpanded" class="mt-4 grid gap-4 border-t border-border pt-4">
        <UiField
          :label="t('settings.fields.enabled')"
          :hint="active ? t('settings.fields.activeProvider') : t('settings.fields.inactiveProvider')"
        >
          <label class="flex min-h-11 items-center gap-2 rounded-xl border border-border bg-surface-muted/35 px-3.5 text-sm text-text-secondary">
            <input
              v-if="kind === 'openai_compatible'"
              v-model="openaiSection.configured"
              type="checkbox"
              class="h-4 w-4 rounded border-border"
            >
            <input
              v-else
              v-model="geminiSection.configured"
              type="checkbox"
              class="h-4 w-4 rounded border-border"
            >
            {{ t('settings.fields.persistSection') }}
          </label>
        </UiField>

        <template v-if="kind === 'openai_compatible'">
          <div class="grid gap-4 xl:grid-cols-2">
            <UiField :label="t('settings.fields.baseUrl')">
              <UiInput v-model="openaiSection.base_url" :placeholder="t('settings.placeholders.baseUrl')" />
            </UiField>

            <UiField :label="t('settings.fields.model')">
              <UiInput v-model="openaiSection.model" :placeholder="t('settings.placeholders.model')" />
            </UiField>

            <UiField :label="t('settings.fields.timeoutSec')" :hint="t('settings.fields.optional')">
              <UiInput v-model="openaiSection.timeout_sec" :placeholder="t('settings.placeholders.timeoutSec')" />
            </UiField>

            <UiField :label="t('settings.fields.outputStrategy')" :hint="t('settings.fields.outputStrategyHint')">
              <UiSelect
                v-model="openaiSection.output_strategy"
                :options="outputStrategyOptions"
              />
            </UiField>

            <UiField :label="t('settings.fields.thinking')" :hint="t('settings.fields.thinkingHint')">
              <UiSelect
                v-model="openaiSection.thinking_mode"
                :options="thinkingModeOptions"
              />
            </UiField>

            <UiField :label="t('settings.fields.apiKey')" :hint="apiKeyHint">
              <UiInput v-model="openaiSection.api_key" type="password" :placeholder="t('settings.placeholders.apiKey')" />
            </UiField>
          </div>

          <UiField :label="t('settings.fields.extraHeaders')" :hint="t('settings.fields.jsonObjectHint')">
            <UiTextarea
              v-model="openaiSection.extra_headers_json"
              :rows="5"
              :placeholder="t('settings.placeholders.extraHeaders')"
            />
          </UiField>
        </template>

        <template v-else>
          <div class="grid gap-4 xl:grid-cols-2">
            <UiField :label="t('settings.fields.model')">
              <UiInput v-model="geminiSection.model" :placeholder="t('settings.placeholders.model')" />
            </UiField>

            <UiField :label="t('settings.fields.apiKey')" :hint="apiKeyHint">
              <UiInput v-model="geminiSection.api_key" type="password" :placeholder="t('settings.placeholders.apiKey')" />
            </UiField>
          </div>

          <div class="grid gap-3 rounded-2xl border border-border/70 bg-surface-muted/25 px-3.5 py-3.5">
            <div class="flex items-center justify-between gap-3">
              <div class="grid gap-1">
                <span class="text-sm font-medium text-text-primary">{{ t('settings.fields.advancedSettings') }}</span>
                <p class="text-xs text-text-secondary">{{ t('settings.fields.geminiAdvancedHint') }}</p>
              </div>
              <button
                type="button"
                class="text-sm font-medium text-accent transition-colors hover:text-accent/80"
                @click="showGeminiAdvanced = !showGeminiAdvanced"
              >
                {{ showGeminiAdvanced ? t('settings.providerCard.hideAdvanced') : t('settings.providerCard.showAdvanced') }}
              </button>
            </div>

            <div v-if="showGeminiAdvanced" class="grid gap-4 xl:grid-cols-2">
              <UiField :label="t('settings.fields.timeoutSec')" :hint="t('settings.fields.optional')">
                <UiInput v-model="geminiSection.timeout_sec" :placeholder="t('settings.placeholders.timeoutSec')" />
              </UiField>

              <UiField :label="t('settings.fields.baseUrl')" :hint="t('settings.fields.geminiBaseUrlHint')" class="xl:col-span-2">
                <UiInput v-model="geminiSection.base_url" :placeholder="t('settings.placeholders.geminiBaseUrl')" />
              </UiField>
            </div>
          </div>
        </template>
    </div>
  </section>
</template>
