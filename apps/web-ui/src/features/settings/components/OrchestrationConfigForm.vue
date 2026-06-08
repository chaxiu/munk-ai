<script setup lang="ts">
import { toRef } from 'vue'
import { useI18n } from 'vue-i18n'

import UiField from '@/shared/ui/UiField.vue'
import UiInput from '@/shared/ui/UiInput.vue'
import type { OrchestrationForm } from '../types'

const props = defineProps<{
  orchestration: OrchestrationForm
}>()

const { t } = useI18n()
const orchestration = toRef(props, 'orchestration')
</script>

<template>
  <div class="grid gap-5">
    <UiField
      class="max-w-md"
      :label="t('settings.fields.maxRetryAttempts')"
    >
      <UiInput v-model="orchestration.max_retry_attempts" :placeholder="t('settings.placeholders.integerValue')" />
    </UiField>

    <div class="grid gap-3 border-t border-border pt-4 md:grid-cols-2">
      <label class="flex min-h-16 items-start gap-3 rounded-xl border border-border bg-surface-muted/20 px-4 py-3.5">
        <input v-model="orchestration.allow_retry_on_failed" type="checkbox" class="mt-0.5 h-4 w-4 rounded border-border">
        <div class="grid gap-1">
          <span class="text-sm font-medium text-text-primary">{{ t('settings.fields.allowRetryOnFailed') }}</span>
          <span class="text-sm text-text-secondary">{{ t('settings.orchestration.allowRetryOnFailedSummary') }}</span>
        </div>
      </label>

      <label class="flex min-h-16 items-start gap-3 rounded-xl border border-border bg-surface-muted/20 px-4 py-3.5">
        <input v-model="orchestration.allow_retry_on_inconclusive" type="checkbox" class="mt-0.5 h-4 w-4 rounded border-border">
        <div class="grid gap-1">
          <span class="text-sm font-medium text-text-primary">{{ t('settings.fields.allowRetryOnInconclusive') }}</span>
          <span class="text-sm text-text-secondary">{{ t('settings.orchestration.allowRetryOnInconclusiveSummary') }}</span>
        </div>
      </label>

      <label class="flex min-h-16 items-start gap-3 rounded-xl border border-border bg-surface-muted/20 px-4 py-3.5 md:col-span-2">
        <input v-model="orchestration.escalate_after_max_attempts" type="checkbox" class="mt-0.5 h-4 w-4 rounded border-border">
        <div class="grid gap-1">
          <span class="text-sm font-medium text-text-primary">{{ t('settings.fields.escalateAfterMaxAttempts') }}</span>
          <span class="text-sm text-text-secondary">{{ t('settings.orchestration.escalateAfterMaxAttemptsSummary') }}</span>
        </div>
      </label>
    </div>
  </div>
</template>
