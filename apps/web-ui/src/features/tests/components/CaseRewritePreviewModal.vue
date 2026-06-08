<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import type { CaseRewritePreviewData } from '@/shared/api/tests'
import UiButton from '@/shared/ui/UiButton.vue'
import UiTextarea from '@/shared/ui/UiTextarea.vue'

defineOptions({
  name: 'CaseRewritePreviewModal',
})

const props = withDefaults(defineProps<{
  open: boolean
  promptValue: string
  generating?: boolean
  preview: CaseRewritePreviewData | null
  errorMessage?: string | null
}>(), {
  generating: false,
  errorMessage: null,
})

const emit = defineEmits<{
  close: []
  generate: []
  apply: []
  'update:promptValue': [value: string]
}>()

const { t } = useI18n()

const promptModel = computed({
  get: () => props.promptValue,
  set: (value: string) => emit('update:promptValue', value),
})

const canGenerate = computed(() => !props.generating && Boolean(props.promptValue.trim()))
const canApply = computed(() => !props.generating && props.preview !== null)

function joinLines(items: string[] | undefined): string {
  return (items ?? []).join('\n')
}
</script>

<template>
  <div
    v-if="open"
    class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/55 p-4 backdrop-blur-sm"
  >
    <div class="flex max-h-[85vh] w-full max-w-4xl flex-col overflow-hidden rounded-2xl border border-border bg-surface-default shadow-panel">
      <header class="border-b border-border px-5 py-4">
        <div class="grid gap-1">
          <h2 class="text-lg font-semibold text-text-primary">{{ t('caseDetail.aiRewrite.title') }}</h2>
          <p class="text-sm text-text-secondary">{{ t('caseDetail.aiRewrite.description') }}</p>
        </div>
      </header>

      <div class="grid gap-4 overflow-y-auto px-5 py-4">
        <label class="grid gap-2">
          <span class="text-sm font-medium text-text-primary">{{ t('caseDetail.aiRewrite.promptLabel') }}</span>
          <UiTextarea
            v-model="promptModel"
            :rows="4"
            :placeholder="t('caseDetail.aiRewrite.promptPlaceholder')"
            :disabled="generating"
          />
        </label>

        <p class="text-sm text-text-secondary">{{ t('caseDetail.aiRewrite.applyHint') }}</p>
        <p v-if="errorMessage" class="text-sm text-error-text">{{ errorMessage }}</p>

        <section class="grid gap-4 rounded-xl border border-border-muted bg-surface-muted p-4">
          <div class="flex items-center justify-between gap-3">
            <h3 class="text-sm font-semibold text-text-primary">{{ t('caseDetail.aiRewrite.previewTitle') }}</h3>
            <UiButton size="sm" variant="secondary" :disabled="!canGenerate" @click="emit('generate')">
              {{ generating ? t('caseDetail.aiRewrite.generating') : t('caseDetail.aiRewrite.generateAction') }}
            </UiButton>
          </div>

          <p v-if="!preview" class="text-sm text-text-secondary">
            {{ t('caseDetail.aiRewrite.previewEmpty') }}
          </p>
          <div v-else class="grid gap-4 text-sm text-text-primary">
            <div class="grid gap-1">
              <span class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('caseDetail.fields.title') }}</span>
              <p class="whitespace-pre-wrap">{{ preview.case.title }}</p>
            </div>
            <div class="grid gap-1">
              <span class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('caseDetail.fields.intent') }}</span>
              <p class="whitespace-pre-wrap">{{ preview.case.intent }}</p>
            </div>
            <div class="grid gap-1">
              <span class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('caseDetail.fields.runnerGoal') }}</span>
              <p class="whitespace-pre-wrap">{{ preview.case.runner_goal }}</p>
            </div>
            <div class="grid gap-4 md:grid-cols-4">
              <div class="grid gap-1">
                <span class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('caseDetail.fields.preconditions') }}</span>
                <p class="whitespace-pre-wrap">{{ joinLines(preview.case.preconditions) }}</p>
              </div>
              <div class="grid gap-1">
                <span class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('caseDetail.fields.expected') }}</span>
                <p class="whitespace-pre-wrap">{{ joinLines(preview.case.expected) }}</p>
              </div>
              <div class="grid gap-1">
                <span class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('caseDetail.fields.procedure') }}</span>
                <p class="whitespace-pre-wrap">{{ joinLines(preview.case.procedure) }}</p>
              </div>
              <div class="grid gap-1">
                <span class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('caseDetail.fields.postAction') }}</span>
                <p class="whitespace-pre-wrap">{{ joinLines(preview.case.post_action) }}</p>
              </div>
            </div>
          </div>
        </section>
      </div>

      <footer class="flex flex-wrap items-center justify-end gap-2 border-t border-border px-5 py-4">
        <UiButton size="sm" variant="secondary" :disabled="generating" @click="emit('close')">
          {{ t('caseDetail.actions.cancel') }}
        </UiButton>
        <UiButton size="sm" variant="primary" :disabled="!canApply" @click="emit('apply')">
          {{ t('caseDetail.aiRewrite.applyAction') }}
        </UiButton>
      </footer>
    </div>
  </div>
</template>
