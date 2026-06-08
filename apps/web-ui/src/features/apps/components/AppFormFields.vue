<script setup lang="ts">
/* eslint-disable vue/no-mutating-props */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import UiField from '@/shared/ui/UiField.vue'
import UiInput from '@/shared/ui/UiInput.vue'
import UiSelect from '@/shared/ui/UiSelect.vue'
import UiTextarea from '@/shared/ui/UiTextarea.vue'
import type { AppFormModel } from '../form'

const props = withDefaults(defineProps<{
  form: AppFormModel
  appIdReadonly?: boolean
}>(), {
  appIdReadonly: false,
})

const { t } = useI18n()
const appKnowledgeError = ref<string | null>(null)

const platformOptions = computed(() => [
  { value: 'android', label: t('apps.filters.android') },
  { value: 'ios', label: t('apps.filters.ios') },
  { value: 'web', label: t('apps.filters.web') },
])

const appKnowledgeStatus = computed(() => {
  if (props.form.appKnowledgeDirty && props.form.appKnowledgeFileName) {
    return t('apps.messages.appKnowledgeSelected', { fileName: props.form.appKnowledgeFileName })
  }
  if (props.form.hasExistingAppKnowledge && props.form.appKnowledgeFileName) {
    return t('apps.messages.appKnowledgeSaved', { fileName: props.form.appKnowledgeFileName })
  }
  return t('apps.messages.appKnowledgeMissing')
})

async function handleAppKnowledgeChange(event: Event) {
  appKnowledgeError.value = null
  const input = event.target as HTMLInputElement | null
  const file = input?.files?.[0]
  if (!file) {
    return
  }
  try {
    const text = await file.text()
    const parsed = JSON.parse(text) as unknown
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error(t('apps.messages.appKnowledgeInvalidShape'))
    }
    props.form.appKnowledgeFileName = file.name
    props.form.appKnowledgeContent = text.trim()
    props.form.appKnowledgeDirty = true
  } catch (error) {
    if (error instanceof SyntaxError) {
      appKnowledgeError.value = t('apps.messages.appKnowledgeInvalidJson')
      return
    }
    appKnowledgeError.value = error instanceof Error ? error.message : String(error)
  }
}
</script>

<template>
  <UiField :label="t('apps.fields.appId')" :hint="appIdReadonly ? t('apps.fields.appIdHint') : undefined">
    <UiInput v-model="props.form.appId" :disabled="appIdReadonly" :placeholder="t('apps.placeholders.appId')" />
  </UiField>

  <UiField :label="t('apps.fields.appName')">
    <UiInput v-model="props.form.appName" :placeholder="t('apps.placeholders.appName')" />
  </UiField>

  <UiField :label="t('apps.fields.platform')">
    <UiSelect v-model="props.form.platform" :options="platformOptions" />
  </UiField>

  <UiField v-if="props.form.platform === 'android'" :label="t('apps.fields.androidPackageName')">
    <UiInput v-model="props.form.androidPackageName" :placeholder="t('apps.placeholders.androidPackageName')" />
  </UiField>

  <UiField v-if="props.form.platform === 'android'" :label="t('apps.fields.androidActivityName')" :hint="t('apps.fields.optional')">
    <UiInput v-model="props.form.androidActivityName" :placeholder="t('apps.placeholders.androidActivityName')" />
  </UiField>

  <UiField v-if="props.form.platform === 'ios'" :label="t('apps.fields.iosBundleId')">
    <UiInput v-model="props.form.iosBundleId" :placeholder="t('apps.placeholders.iosBundleId')" />
  </UiField>

  <UiField v-if="props.form.platform === 'web'" :label="t('apps.fields.webBaseUrl')">
    <UiInput v-model="props.form.webBaseUrl" :placeholder="t('apps.placeholders.webBaseUrl')" />
  </UiField>

  <UiField v-if="props.form.platform === 'web'" :label="t('apps.fields.webOrigin')" :hint="t('apps.fields.optional')">
    <UiInput v-model="props.form.webOrigin" :placeholder="t('apps.placeholders.webOrigin')" />
  </UiField>

  <UiField :label="t('apps.fields.introductionMarkdown')">
    <UiTextarea
      v-model="props.form.introductionMarkdown"
      :placeholder="t('apps.placeholders.introductionMarkdown')"
      :rows="10"
    />
  </UiField>

  <UiField :label="t('apps.fields.appKnowledgeFile')" :hint="t('apps.fields.appKnowledgeFileHint')">
    <div class="grid gap-2">
      <input
        class="block w-full rounded-xl border border-border bg-surface-default px-3 py-2 text-sm text-text-primary file:mr-3 file:rounded-lg file:border-0 file:bg-accent-soft file:px-3 file:py-2 file:text-sm file:font-medium file:text-accent hover:border-border-strong"
        type="file"
        accept=".json,application/json"
        @change="handleAppKnowledgeChange"
      >
      <p class="text-xs text-text-secondary">{{ appKnowledgeStatus }}</p>
      <p v-if="appKnowledgeError" class="text-xs text-status-danger">{{ appKnowledgeError }}</p>
    </div>
  </UiField>
</template>
