<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { getKnowledgePayloadSections } from '@/features/apps/knowledgeFieldConfig'
import type { KnowledgeEditorMode, KnowledgePayloadDraft } from '@/features/apps/knowledgeEditor'
import type { KnowledgeCardType } from '@/shared/api/knowledge'
import UiField from '@/shared/ui/UiField.vue'
import UiInput from '@/shared/ui/UiInput.vue'
import UiTextarea from '@/shared/ui/UiTextarea.vue'
import KnowledgeStringListField from './KnowledgeStringListField.vue'

const props = withDefaults(defineProps<{
  cardType: KnowledgeCardType
  editorMode: KnowledgeEditorMode
  disabled?: boolean
  payloadError?: string | null
  payloadFieldErrors?: Record<string, string>
}>(), {
  disabled: false,
  payloadError: null,
  payloadFieldErrors: () => ({}),
})

const payloadDraft = defineModel<KnowledgePayloadDraft>('payloadDraft', { required: true })
const jsonModeText = defineModel<string>('jsonModeText', { required: true })

const { t } = useI18n()

const sections = computed(() => getKnowledgePayloadSections(props.cardType))

function getStringValue(key: string): string {
  const value = payloadDraft.value[key]
  return typeof value === 'string' ? value : ''
}

function setStringValue(key: string, value: string) {
  payloadDraft.value = {
    ...payloadDraft.value,
    [key]: value,
  }
}

function getArrayValue(key: string): string[] {
  const value = payloadDraft.value[key]
  return Array.isArray(value) ? value : []
}

function setArrayValue(key: string, value: string[]) {
  payloadDraft.value = {
    ...payloadDraft.value,
    [key]: value,
  }
}

function translateFieldError(key: string): string | null {
  const error = props.payloadFieldErrors[key]
  if (!error) {
    return null
  }
  if (error === 'field-required') {
    return t('apps.knowledge.messages.requiredField')
  }
  return error
}
</script>

<template>
  <div class="grid gap-4">
    <UiField
      v-if="props.editorMode === 'json'"
      :label="$t('apps.knowledge.fields.payload')"
      :hint="$t('apps.knowledge.fields.payloadHint')"
      :error="props.payloadError"
    >
      <UiTextarea
        v-model="jsonModeText"
        :rows="14"
        :disabled="props.disabled"
        :placeholder="$t('apps.knowledge.fields.payloadJsonPlaceholder')"
      />
    </UiField>

    <template v-else>
      <div
        v-for="section in sections"
        :key="section.key"
        class="grid gap-4"
      >
        <p v-if="section.titleKey" class="text-sm font-medium text-text-primary">{{ t(section.titleKey) }}</p>

        <UiField
          v-for="field in section.fields"
          :key="field.key"
          :label="t(field.labelKey)"
          :hint="field.descriptionKey ? t(field.descriptionKey) : undefined"
          :error="translateFieldError(field.key)"
        >
          <UiInput
            v-if="field.kind === 'text'"
            :model-value="getStringValue(field.key)"
            :disabled="props.disabled"
            :placeholder="field.placeholderKey ? t(field.placeholderKey) : ''"
            @update:model-value="setStringValue(field.key, $event)"
          />
          <UiTextarea
            v-else-if="field.kind === 'textarea'"
            :model-value="getStringValue(field.key)"
            :disabled="props.disabled"
            :rows="4"
            :placeholder="field.placeholderKey ? t(field.placeholderKey) : ''"
            @update:model-value="setStringValue(field.key, $event)"
          />
          <KnowledgeStringListField
            v-else
            :model-value="getArrayValue(field.key)"
            :disabled="props.disabled"
            :placeholder="field.placeholderKey ? t(field.placeholderKey) : ''"
            @update:model-value="setArrayValue(field.key, $event)"
          />
        </UiField>
      </div>
    </template>
  </div>
</template>
