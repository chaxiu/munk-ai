<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import UiButton from '@/shared/ui/UiButton.vue'
import UiInput from '@/shared/ui/UiInput.vue'
import UiTextarea from '@/shared/ui/UiTextarea.vue'

defineOptions({
  name: 'CreateCaseModal',
})

const props = withDefaults(defineProps<{
  open: boolean
  titleValue: string
  intentValue: string
  runnerGoalValue: string
  creating?: boolean
  errorMessage?: string | null
}>(), {
  creating: false,
  errorMessage: null,
})

const emit = defineEmits<{
  close: []
  confirm: []
  'update:titleValue': [value: string]
  'update:intentValue': [value: string]
  'update:runnerGoalValue': [value: string]
}>()

const { t } = useI18n()

const titleModel = computed({
  get: () => props.titleValue,
  set: (value: string) => emit('update:titleValue', value),
})

const intentModel = computed({
  get: () => props.intentValue,
  set: (value: string) => emit('update:intentValue', value),
})

const runnerGoalModel = computed({
  get: () => props.runnerGoalValue,
  set: (value: string) => emit('update:runnerGoalValue', value),
})

const submitDisabled = computed(() => (
  props.creating
  || !props.titleValue.trim()
  || !props.intentValue.trim()
  || !props.runnerGoalValue.trim()
))
</script>

<template>
  <div
    v-if="open"
    class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/55 p-4 backdrop-blur-sm"
  >
    <div class="flex w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-border bg-surface-default shadow-panel">
      <header class="border-b border-border px-5 py-4">
        <div class="grid gap-1">
          <h2 class="text-lg font-semibold text-text-primary">{{ t('planDetail.createCaseTitle') }}</h2>
          <p class="text-sm text-text-secondary">{{ t('planDetail.createCaseDescription') }}</p>
        </div>
      </header>

      <div class="grid gap-4 px-5 py-4">
        <label class="grid gap-2">
          <span class="text-sm font-medium text-text-primary">{{ t('caseDetail.fields.title') }}</span>
          <UiInput
            v-model="titleModel"
            :placeholder="t('planDetail.createCasePlaceholder')"
            :disabled="creating"
          />
        </label>
        <label class="grid gap-2">
          <span class="text-sm font-medium text-text-primary">{{ t('caseDetail.fields.intent') }}</span>
          <UiTextarea
            v-model="intentModel"
            :rows="4"
            :placeholder="t('planDetail.createCaseIntentPlaceholder')"
            :disabled="creating"
          />
        </label>
        <label class="grid gap-2">
          <span class="text-sm font-medium text-text-primary">{{ t('caseDetail.fields.runnerGoal') }}</span>
          <UiInput
            v-model="runnerGoalModel"
            :placeholder="t('planDetail.createCaseRunnerGoalPlaceholder')"
            :disabled="creating"
          />
        </label>
        <p v-if="errorMessage" class="text-sm text-error-text">{{ errorMessage }}</p>
      </div>

      <footer class="flex flex-wrap items-center justify-end gap-2 border-t border-border px-5 py-4">
        <UiButton size="sm" variant="secondary" :disabled="creating" @click="emit('close')">
          {{ t('caseDetail.actions.cancel') }}
        </UiButton>
        <UiButton size="sm" variant="primary" :disabled="submitDisabled" @click="emit('confirm')">
          {{ creating ? t('planDetail.creating') : t('planDetail.addCaseAction') }}
        </UiButton>
      </footer>
    </div>
  </div>
</template>
