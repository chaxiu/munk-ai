<script setup lang="ts">
import { Plus, Trash2 } from '@lucide/vue'
import { toRef } from 'vue'
import { useI18n } from 'vue-i18n'

import StringMapEditor from '@/shared/components/StringMapEditor.vue'
import UiButton from '@/shared/ui/UiButton.vue'
import UiField from '@/shared/ui/UiField.vue'
import UiInput from '@/shared/ui/UiInput.vue'
import UiTextarea from '@/shared/ui/UiTextarea.vue'
import type { StringMapEntry } from '@/shared/lib/stringMapForm'

import { createEmptyHttpBaseFormItem, type TestEnvForm } from '../types'

const props = defineProps<{
  testEnv: TestEnvForm
}>()

const { t } = useI18n()
const testEnv = toRef(props, 'testEnv')

function addBase() {
  testEnv.value.bases = [...testEnv.value.bases, createEmptyHttpBaseFormItem()]
}

function removeBase(index: number) {
  testEnv.value.bases = testEnv.value.bases.filter((_, itemIndex) => itemIndex !== index)
}

function updateBaseName(index: number, value: string) {
  testEnv.value.bases = testEnv.value.bases.map((item, itemIndex) => (
    itemIndex === index ? { ...item, name: value } : item
  ))
}

function updateBaseUrl(index: number, value: string) {
  testEnv.value.bases = testEnv.value.bases.map((item, itemIndex) => (
    itemIndex === index ? { ...item, url: value } : item
  ))
}

function updateBaseHeaders(index: number, value: StringMapEntry[]) {
  testEnv.value.bases = testEnv.value.bases.map((item, itemIndex) => (
    itemIndex === index ? { ...item, headers: value } : item
  ))
}
</script>

<template>
  <div class="grid gap-4">
    <div class="grid gap-2">
      <h3 class="text-sm font-semibold text-text-primary">{{ t('settings.testEnv.basesTitle') }}</h3>
      <p class="text-sm text-text-secondary">{{ t('settings.testEnv.basesDescription') }}</p>
    </div>

    <div v-if="testEnv.bases.length === 0" class="text-sm text-text-secondary">
      {{ t('settings.testEnv.basesEmpty') }}
    </div>

    <div
      v-for="(base, index) in testEnv.bases"
      :key="`base-${index}`"
      class="grid gap-4 rounded-2xl border border-border bg-surface-muted/20 p-4"
    >
      <div class="flex items-center justify-between gap-3">
        <h4 class="text-sm font-medium text-text-primary">{{ t('settings.testEnv.baseItemTitle', { index: index + 1 }) }}</h4>
        <UiButton
          type="button"
          variant="ghost"
          :aria-label="t('settings.testEnv.removeBase')"
          @click="removeBase(index)"
        >
          <Trash2 class="h-4 w-4" />
        </UiButton>
      </div>

      <UiField :label="t('settings.fields.testEnvBaseName')" required>
        <UiInput
          :model-value="base.name"
          :placeholder="t('settings.placeholders.testEnvBaseName')"
          @update:model-value="updateBaseName(index, $event)"
        />
      </UiField>

      <UiField :label="t('settings.fields.testEnvBaseUrl')" required>
        <UiInput
          :model-value="base.url"
          :placeholder="t('settings.placeholders.testEnvBaseUrl')"
          @update:model-value="updateBaseUrl(index, $event)"
        />
      </UiField>

      <UiField
        :label="t('settings.fields.testEnvBaseHeaders')"
        optional
        :description="t('settings.fieldDescriptions.testEnvBaseHeaders')"
      >
        <StringMapEditor
          :model-value="base.headers"
          :key-placeholder="t('settings.placeholders.testEnvBaseHeaderKey')"
          :value-placeholder="t('settings.placeholders.testEnvBaseHeaderValue')"
          @update:model-value="updateBaseHeaders(index, $event)"
        />
      </UiField>
    </div>

    <UiButton type="button" variant="secondary" @click="addBase">
      <Plus class="h-4 w-4" />
      {{ t('settings.testEnv.addBase') }}
    </UiButton>

    <UiField
      :label="t('settings.fields.allowedExec')"
      optional
      :description="t('settings.fieldDescriptions.allowedExec')"
    >
      <UiTextarea
        v-model="testEnv.allowed_exec_text"
        :rows="5"
        :placeholder="t('settings.placeholders.allowedExec')"
      />
    </UiField>
  </div>
</template>
