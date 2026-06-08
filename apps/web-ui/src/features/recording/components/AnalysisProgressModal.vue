<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import type { OperationDetailData, OperationEventsData } from '@/shared/api/operations'
import UiButton from '@/shared/ui/UiButton.vue'
import { useTime } from '@/shared/time/useTime'

const props = defineProps<{
  open: boolean
  operation: OperationDetailData | null
  events: NonNullable<OperationEventsData['items']>
  errorMessage: string | null
  canExport: boolean
}>()

const emit = defineEmits<{
  close: []
  retry: []
  export: []
}>()

const { t } = useI18n()
const time = useTime({ relative: true })

const progress = computed(() => props.operation?.progress ?? {})
const status = computed(() => props.operation?.status ?? null)
const phase = computed(() => String(progress.value.phase ?? ''))
const completedSteps = computed(() => Number(progress.value.completed_steps ?? 0))
const totalSteps = computed(() => Number(progress.value.total_steps ?? 0))
const operationError = computed(() =>
  props.errorMessage
  ?? props.operation?.error_message
  ?? null
)

const progressLabel = computed(() => {
  if (phase.value === 'loading') {
    return t('recording.analysisProgress.loading')
  }
  if (phase.value === 'analyzing_steps') {
    return t('recording.analysisProgress.steps', {
      completed: completedSteps.value,
      total: totalSteps.value,
      current: progress.value.current_step_seq ?? completedSteps.value,
    })
  }
  if (phase.value === 'finalizing') {
    return t('recording.analysisProgress.finalizing')
  }
  if (status.value === 'succeeded') {
    return t('recording.analysisProgress.completed')
  }
  if (status.value === 'failed') {
    return t('recording.analysisProgress.failed')
  }
  return t('recording.analysisProgress.waiting')
})

const title = computed(() => {
  if (status.value === 'succeeded') {
    return t('recording.analysisModal.successTitle')
  }
  if (status.value === 'failed') {
    return t('recording.analysisModal.failureTitle')
  }
  return t('recording.analysisModal.runningTitle')
})

const subtitle = computed(() => {
  if (status.value === 'succeeded') {
    return t('recording.analysisModal.successSubtitle')
  }
  if (status.value === 'failed') {
    return t('recording.analysisModal.failureSubtitle')
  }
  return t('recording.analysisModal.runningSubtitle')
})
</script>

<template>
  <div
    v-if="open"
    class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/55 p-4 backdrop-blur-sm"
  >
    <div class="flex max-h-[80vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-border bg-surface-default shadow-panel">
      <header class="border-b border-border px-5 py-4">
        <div class="flex items-start justify-between gap-4">
          <div class="grid gap-1">
            <h2 class="text-lg font-semibold text-text-primary">{{ title }}</h2>
            <p class="text-sm text-text-secondary">{{ subtitle }}</p>
          </div>
          <UiButton size="sm" variant="secondary" @click="emit('close')">
            {{ t('recording.analysisModal.close') }}
          </UiButton>
        </div>
      </header>

      <div class="grid gap-4 overflow-y-auto px-5 py-4">
        <div class="grid gap-3 rounded-xl border border-border-muted bg-surface-muted p-4">
          <div class="flex items-center justify-between gap-3">
            <span class="text-sm font-medium text-text-primary">{{ progressLabel }}</span>
            <span
              class="inline-flex rounded-full px-2.5 py-1 text-xs font-semibold"
              :class="status === 'failed'
                ? 'bg-error-bg text-error-text'
                : status === 'succeeded'
                  ? 'bg-success-bg text-success-text'
                  : 'bg-accent-soft text-accent'"
            >
              {{ status ?? 'queued' }}
            </span>
          </div>
          <div v-if="totalSteps > 0" class="grid gap-2">
            <div class="h-2 overflow-hidden rounded-full bg-surface-default">
              <div
                class="h-full rounded-full bg-accent transition-[width]"
                :style="{ width: `${Math.max(8, Math.min(100, (completedSteps / totalSteps) * 100))}%` }"
              />
            </div>
            <span class="text-xs text-text-secondary">
              {{ t('recording.analysisProgress.stepCounter', { completed: completedSteps, total: totalSteps }) }}
            </span>
          </div>
          <div v-if="operation?.operation_id" class="grid gap-1">
            <label class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('recording.fields.operationId') }}</label>
            <span class="break-all text-sm text-text-primary">{{ operation.operation_id }}</span>
          </div>
        </div>

        <div
          v-if="operationError"
          class="grid gap-2 rounded-xl border border-error-text/20 bg-error-bg p-4"
        >
          <label class="text-xs font-semibold uppercase tracking-[0.18em] text-error-text">{{ t('recording.fields.failure') }}</label>
          <span class="text-sm text-error-text">{{ operationError }}</span>
        </div>

        <div class="grid gap-3">
          <div class="flex items-center justify-between gap-3">
            <h3 class="text-sm font-semibold text-text-primary">{{ t('recording.analysisModal.timeline') }}</h3>
            <span class="text-xs text-text-secondary">{{ events.length }}</span>
          </div>
          <div
            v-if="events.length === 0"
            class="rounded-xl border border-dashed border-border-muted px-4 py-5 text-sm text-text-secondary"
          >
            {{ t('recording.analysisModal.noEvents') }}
          </div>
          <div v-else class="grid gap-3">
            <div
              v-for="event in events"
              :key="`${event.seq}-${event.event_type}`"
              class="grid gap-1 rounded-xl border border-border-muted bg-surface-muted px-4 py-3"
            >
              <div class="flex items-center justify-between gap-3">
                <span class="text-sm font-medium text-text-primary">{{ event.message || event.event_type }}</span>
                <time
                  class="text-xs text-text-secondary"
                  :datetime="time.datetime(event.timestamp) ?? undefined"
                  :title="time.tooltip(event.timestamp)"
                >
                  {{ time.relative(event.timestamp) }}
                </time>
              </div>
              <span class="text-xs text-text-muted">{{ event.event_type }}</span>
            </div>
          </div>
        </div>
      </div>

      <footer class="flex flex-wrap items-center justify-end gap-2 border-t border-border px-5 py-4">
        <UiButton
          v-if="status === 'failed'"
          size="sm"
          variant="secondary"
          @click="emit('retry')"
        >
          {{ t('recording.analysisModal.retry') }}
        </UiButton>
        <UiButton
          v-if="status === 'succeeded' && canExport"
          size="sm"
          variant="primary"
          @click="emit('export')"
        >
          {{ t('recording.analysisModal.export') }}
        </UiButton>
        <UiButton size="sm" variant="secondary" @click="emit('close')">
          {{ t('recording.analysisModal.close') }}
        </UiButton>
      </footer>
    </div>
  </div>
</template>
