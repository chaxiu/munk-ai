<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { formatStartModeLabel } from '@/features/tests/startModeLabels'
import UiButton from '@/shared/ui/UiButton.vue'
import UiSelect from '@/shared/ui/UiSelect.vue'
import UiTextarea from '@/shared/ui/UiTextarea.vue'

defineOptions({
  name: 'CaseFieldEditModal',
})

const props = withDefaults(defineProps<{
  open: boolean
  fieldKey: string | null
  fieldLabel: string
  draftValue: string
  saving?: boolean
  errorMessage?: string | null
}>(), {
  saving: false,
  errorMessage: null,
})

const emit = defineEmits<{
  close: []
  confirm: []
  'update:draftValue': [value: string]
}>()

const { t } = useI18n()

const isStartModeField = computed(() => props.fieldKey === 'start_mode')
const isListField = computed(() => ['preconditions', 'expected', 'procedure'].includes(props.fieldKey ?? ''))
const draftValueModel = computed({
  get: () => props.draftValue,
  set: (value: string) => emit('update:draftValue', value),
})
const modalDescription = computed(() => {
  if (isListField.value) {
    return t('caseDetail.editModal.listHint')
  }
  if (props.fieldKey === 'start_page_id') {
    return t('caseDetail.editModal.emptyValueHint')
  }
  return t('caseDetail.editModal.description')
})
const startModeOptions = computed(() => ([
  { label: formatStartModeLabel('reset', t), value: 'reset' },
  { label: formatStartModeLabel('resume', t), value: 'resume' },
]))
</script>

<template>
  <div
    v-if="open"
    class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/55 p-4 backdrop-blur-sm"
  >
    <div class="flex max-h-[80vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-border bg-surface-default shadow-panel">
      <header class="border-b border-border px-5 py-4">
        <div class="grid gap-1">
          <h2 class="text-lg font-semibold text-text-primary">
            {{ t('caseDetail.editModal.title', { field: fieldLabel }) }}
          </h2>
          <p class="text-sm text-text-secondary">{{ modalDescription }}</p>
        </div>
      </header>

      <div class="grid gap-4 overflow-y-auto px-5 py-4">
        <div class="grid gap-2">
          <label class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ fieldLabel }}</label>
          <UiSelect
            v-if="isStartModeField"
            v-model="draftValueModel"
            :options="startModeOptions"
            :placeholder="t('caseDetail.startModePlaceholder')"
            :disabled="saving"
          />
          <UiTextarea
            v-else
            v-model="draftValueModel"
            :rows="isListField ? 8 : 6"
            :disabled="saving"
          />
        </div>
        <p v-if="errorMessage" class="text-sm text-error-text">{{ errorMessage }}</p>
      </div>

      <footer class="flex flex-wrap items-center justify-end gap-2 border-t border-border px-5 py-4">
        <UiButton size="sm" variant="secondary" :disabled="saving" @click="emit('close')">
          {{ t('caseDetail.actions.cancel') }}
        </UiButton>
        <UiButton size="sm" variant="primary" :disabled="saving" @click="emit('confirm')">
          {{ saving ? t('caseDetail.editModal.saving') : t('caseDetail.actions.save') }}
        </UiButton>
      </footer>
    </div>
  </div>
</template>
