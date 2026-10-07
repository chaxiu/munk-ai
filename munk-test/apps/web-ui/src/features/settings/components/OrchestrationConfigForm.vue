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
      optional
      :description="t('settings.fieldDescriptions.maxRetryAttempts')"
    >
      <UiInput v-model="orchestration.max_retry_attempts" :placeholder="t('settings.placeholders.integerValue')" />
    </UiField>

    <div class="grid gap-3 border-t border-border pt-4 md:grid-cols-2">
      <UiField
        :label="t('settings.fields.allowRetryOnFailed')"
        optional
        :description="t('settings.fieldDescriptions.allowRetryOnFailed')"
      >
        <label class="flex min-h-16 items-start gap-3 rounded-xl border border-border bg-surface-muted/20 px-4 py-3.5">
          <input v-model="orchestration.allow_retry_on_failed" type="checkbox" class="mt-0.5 h-4 w-4 rounded border-border">
          <span class="text-sm text-text-secondary">{{ t('settings.orchestration.allowRetryOnFailedSummary') }}</span>
        </label>
      </UiField>

      <UiField
        :label="t('settings.fields.allowRetryOnInconclusive')"
        optional
        :description="t('settings.fieldDescriptions.allowRetryOnInconclusive')"
      >
        <label class="flex min-h-16 items-start gap-3 rounded-xl border border-border bg-surface-muted/20 px-4 py-3.5">
          <input v-model="orchestration.allow_retry_on_inconclusive" type="checkbox" class="mt-0.5 h-4 w-4 rounded border-border">
          <span class="text-sm text-text-secondary">{{ t('settings.orchestration.allowRetryOnInconclusiveSummary') }}</span>
        </label>
      </UiField>

      <UiField
        class="md:col-span-2"
        :label="t('settings.fields.escalateAfterMaxAttempts')"
        optional
        :description="t('settings.fieldDescriptions.escalateAfterMaxAttempts')"
      >
        <label class="flex min-h-16 items-start gap-3 rounded-xl border border-border bg-surface-muted/20 px-4 py-3.5">
          <input v-model="orchestration.escalate_after_max_attempts" type="checkbox" class="mt-0.5 h-4 w-4 rounded border-border">
          <span class="text-sm text-text-secondary">{{ t('settings.orchestration.escalateAfterMaxAttemptsSummary') }}</span>
        </label>
      </UiField>
    </div>
  </div>
</template>
