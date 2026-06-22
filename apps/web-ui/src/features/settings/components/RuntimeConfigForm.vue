<script setup lang="ts">
import { computed, toRef } from 'vue'
import { useI18n } from 'vue-i18n'

import UiField from '@/shared/ui/UiField.vue'
import UiInput from '@/shared/ui/UiInput.vue'
import UiSelect from '@/shared/ui/UiSelect.vue'
import type { RuntimeForm } from '../types'

const props = defineProps<{
  runtime: RuntimeForm
}>()

const { t } = useI18n()
const runtime = toRef(props, 'runtime')
const settleModeOptions = computed(() => [
  { value: 'strict', label: t('settings.settleMode.strict') },
  { value: 'ratio', label: t('settings.settleMode.ratio') },
  { value: 'delay', label: t('settings.settleMode.delay') },
])
</script>

<template>
  <div class="grid gap-5">
    <section class="grid gap-3 border-b border-border pb-4 last:border-b-0 last:pb-0">
      <div class="grid gap-1">
        <h3 class="text-sm font-semibold text-text-primary">{{ t('settings.runtimeGroups.generation') }}</h3>
        <p class="text-sm text-text-secondary">{{ t('settings.runtimeGroupDescriptions.generation') }}</p>
      </div>
      <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <UiField :label="t('settings.fields.maxTokens')" optional :description="t('settings.fieldDescriptions.maxTokens')">
          <UiInput v-model="runtime.max_tokens" :placeholder="t('settings.placeholders.integerValue')" />
        </UiField>
        <UiField :label="t('settings.fields.temperature')" optional :description="t('settings.fieldDescriptions.temperature')">
          <UiInput v-model="runtime.temperature" :placeholder="t('settings.placeholders.numberValue')" />
        </UiField>
      </div>
    </section>

    <section class="grid gap-3 border-b border-border pb-4 last:border-b-0 last:pb-0">
      <div class="grid gap-1">
        <h3 class="text-sm font-semibold text-text-primary">{{ t('settings.runtimeGroups.executionLoop') }}</h3>
        <p class="text-sm text-text-secondary">{{ t('settings.runtimeGroupDescriptions.executionLoop') }}</p>
      </div>
      <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <UiField :label="t('settings.fields.maxSteps')" optional :description="t('settings.fieldDescriptions.maxSteps')">
          <UiInput v-model="runtime.max_steps" :placeholder="t('settings.placeholders.integerValue')" />
        </UiField>
        <UiField :label="t('settings.fields.maxSeconds')" optional :description="t('settings.fieldDescriptions.maxSeconds')">
          <UiInput v-model="runtime.max_seconds" :placeholder="t('settings.placeholders.numberValue')" />
        </UiField>
        <UiField :label="t('settings.fields.interval')" optional :description="t('settings.fieldDescriptions.interval')">
          <UiInput v-model="runtime.interval" :placeholder="t('settings.placeholders.numberValue')" />
        </UiField>
        <UiField :label="t('settings.fields.settleTimeout')" optional :description="t('settings.fieldDescriptions.settleTimeout')">
          <UiInput v-model="runtime.settle_timeout" :placeholder="t('settings.placeholders.numberValue')" />
        </UiField>
        <UiField :label="t('settings.fields.settleMode')" optional :description="t('settings.fieldDescriptions.settleMode')">
          <UiSelect
            v-model="runtime.settle_mode"
            :options="settleModeOptions"
          />
        </UiField>
        <UiField
          :label="t('settings.fields.settleOcrOnly')"
          optional
          :description="t('settings.fieldDescriptions.settleOcrOnly')"
        >
          <label class="flex min-h-11 items-center gap-2 rounded-xl border border-border bg-surface-muted/35 px-3.5 text-sm text-text-secondary">
            <input v-model="runtime.settle_ocr_only" type="checkbox" class="h-4 w-4 rounded border-border">
            {{ t('settings.fields.settleOcrOnlyToggle') }}
          </label>
        </UiField>
        <UiField
          :label="t('settings.fields.settleRatioThreshold')"
          optional
          :description="t('settings.fieldDescriptions.settleRatioThreshold')"
        >
          <UiInput v-model="runtime.settle_ratio_threshold" :placeholder="t('settings.placeholders.numberValue')" />
        </UiField>
        <UiField :label="t('settings.fields.settleDelaySec')" optional :description="t('settings.fieldDescriptions.settleDelaySec')">
          <UiInput v-model="runtime.settle_delay_sec" :placeholder="t('settings.placeholders.numberValue')" />
        </UiField>
      </div>
    </section>

    <section class="grid gap-3">
      <div class="grid gap-1">
        <h3 class="text-sm font-semibold text-text-primary">{{ t('settings.runtimeGroups.vision') }}</h3>
        <p class="text-sm text-text-secondary">{{ t('settings.runtimeGroupDescriptions.vision') }}</p>
      </div>
      <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <UiField :label="t('settings.fields.maxSide')" optional :description="t('settings.fieldDescriptions.maxSide')">
          <UiInput v-model="runtime.max_side" :placeholder="t('settings.placeholders.integerValue')" />
        </UiField>
        <UiField :label="t('settings.fields.vlMaxSide')" optional :description="t('settings.fieldDescriptions.vlMaxSide')">
          <UiInput v-model="runtime.vl_max_side" :placeholder="t('settings.placeholders.integerValue')" />
        </UiField>
        <UiField :label="t('settings.fields.iconConf')" optional :description="t('settings.fieldDescriptions.iconConf')">
          <UiInput v-model="runtime.icon_conf" :placeholder="t('settings.placeholders.numberValue')" />
        </UiField>
        <UiField
          :label="t('settings.fields.runnerIncludeScreenshot')"
          optional
          :description="t('settings.fieldDescriptions.runnerIncludeScreenshot')"
        >
          <label class="flex min-h-11 items-center gap-2 rounded-xl border border-border bg-surface-muted/35 px-3.5 text-sm text-text-secondary">
            <input v-model="runtime.runner_include_screenshot" type="checkbox" class="h-4 w-4 rounded border-border">
            {{ t('settings.fields.runnerIncludeScreenshotToggle') }}
          </label>
        </UiField>
      </div>
    </section>
  </div>
</template>
