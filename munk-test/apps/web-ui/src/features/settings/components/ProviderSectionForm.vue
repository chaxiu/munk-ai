<script setup lang="ts">
import { ChevronDown } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import UiField from '@/shared/ui/UiField.vue'
import UiInput from '@/shared/ui/UiInput.vue'
import UiSelect from '@/shared/ui/UiSelect.vue'
import UiTextarea from '@/shared/ui/UiTextarea.vue'
import {
  getProviderFieldMeta,
  isProviderFieldRequired,
  type GeminiProviderFieldKey,
  type GeminiSectionForm,
  type OpenAIProviderFieldKey,
  type OpenAISectionForm,
  type ProviderKind,
} from '../types'

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

const providerRequirement = computed(() => (
  props.active
    ? t('settings.fieldDescriptions.common.providerRequiredWhenActive')
    : t('settings.fieldDescriptions.common.providerStandbyOptional')
))
const apiKeyPreserveRule = computed(() => (
  props.section.api_key_configured
    ? t('settings.fieldDescriptions.common.secretConfiguredKeep')
    : t('settings.fieldDescriptions.common.secretEmptySkipped')
))

function openaiDescription(field: OpenAIProviderFieldKey): string {
  return t(getProviderFieldMeta('openai_compatible', field).descriptionKey, {
    requirement: providerRequirement.value,
    preserveRule: apiKeyPreserveRule.value,
  })
}

function geminiDescription(field: GeminiProviderFieldKey): string {
  return t(getProviderFieldMeta('gemini', field).descriptionKey, {
    requirement: providerRequirement.value,
    preserveRule: apiKeyPreserveRule.value,
  })
}

function openaiRequired(field: OpenAIProviderFieldKey): boolean {
  return isProviderFieldRequired('openai_compatible', field, props.active)
}

function geminiRequired(field: GeminiProviderFieldKey): boolean {
  return isProviderFieldRequired('gemini', field, props.active)
}

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
        <template v-if="kind === 'openai_compatible'">
          <div class="grid gap-4 xl:grid-cols-2">
            <UiField
              :label="t('settings.fields.baseUrl')"
              :required="openaiRequired('base_url')"
              :optional="!openaiRequired('base_url')"
              :description="openaiDescription('base_url')"
            >
              <UiInput v-model="openaiSection.base_url" :placeholder="t('settings.placeholders.baseUrl')" />
            </UiField>

            <UiField
              :label="t('settings.fields.model')"
              :required="openaiRequired('model')"
              :optional="!openaiRequired('model')"
              :description="openaiDescription('model')"
            >
              <UiInput v-model="openaiSection.model" :placeholder="t('settings.placeholders.model')" />
            </UiField>

            <UiField
              :label="t('settings.fields.timeoutSec')"
              optional
              :description="openaiDescription('timeout_sec')"
            >
              <UiInput v-model="openaiSection.timeout_sec" :placeholder="t('settings.placeholders.timeoutSec')" />
            </UiField>

            <UiField
              :label="t('settings.fields.outputStrategy')"
              optional
              :description="openaiDescription('output_strategy')"
            >
              <UiSelect
                v-model="openaiSection.output_strategy"
                :options="outputStrategyOptions"
              />
            </UiField>

            <UiField
              :label="t('settings.fields.thinking')"
              optional
              :description="openaiDescription('thinking_mode')"
            >
              <UiSelect
                v-model="openaiSection.thinking_mode"
                :options="thinkingModeOptions"
              />
            </UiField>

            <UiField
              :label="t('settings.fields.apiKey')"
              optional
              :description="openaiDescription('api_key')"
            >
              <UiInput v-model="openaiSection.api_key" type="password" :placeholder="t('settings.placeholders.apiKey')" />
            </UiField>
          </div>

          <UiField
            :label="t('settings.fields.extraHeaders')"
            optional
            :description="openaiDescription('extra_headers_json')"
          >
            <UiTextarea
              v-model="openaiSection.extra_headers_json"
              :rows="5"
              :placeholder="t('settings.placeholders.extraHeaders')"
            />
          </UiField>
        </template>

        <template v-else>
          <div class="grid gap-4 xl:grid-cols-2">
            <UiField
              :label="t('settings.fields.model')"
              :required="geminiRequired('model')"
              :optional="!geminiRequired('model')"
              :description="geminiDescription('model')"
            >
              <UiInput v-model="geminiSection.model" :placeholder="t('settings.placeholders.model')" />
            </UiField>

            <UiField
              :label="t('settings.fields.apiKey')"
              optional
              :description="geminiDescription('api_key')"
            >
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
              <UiField
                :label="t('settings.fields.timeoutSec')"
                optional
                :description="geminiDescription('timeout_sec')"
              >
                <UiInput v-model="geminiSection.timeout_sec" :placeholder="t('settings.placeholders.timeoutSec')" />
              </UiField>

              <UiField
                :label="t('settings.fields.credentialsPath')"
                optional
                :description="geminiDescription('credentials_path')"
              >
                <UiInput v-model="geminiSection.credentials_path" :placeholder="t('settings.placeholders.credentialsPath')" />
              </UiField>

              <UiField
                class="xl:col-span-2"
                :label="t('settings.fields.baseUrl')"
                optional
                :description="geminiDescription('base_url')"
              >
                <UiInput v-model="geminiSection.base_url" :placeholder="t('settings.placeholders.geminiBaseUrl')" />
              </UiField>

              <UiField
                :label="t('settings.fields.project')"
                optional
                :description="geminiDescription('project')"
              >
                <UiInput v-model="geminiSection.project" :placeholder="t('settings.placeholders.project')" />
              </UiField>

              <UiField
                :label="t('settings.fields.location')"
                optional
                :description="geminiDescription('location')"
              >
                <UiInput v-model="geminiSection.location" :placeholder="t('settings.placeholders.location')" />
              </UiField>
            </div>
          </div>
        </template>
    </div>
  </section>
</template>
