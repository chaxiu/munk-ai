<script setup lang="ts">
import { toRef } from 'vue'
import { useI18n } from 'vue-i18n'

import UiField from '@/shared/ui/UiField.vue'
import UiInput from '@/shared/ui/UiInput.vue'
import type { RuntimeForm } from '../types'

const props = defineProps<{
  runtime: RuntimeForm
}>()

const { t } = useI18n()
const runtime = toRef(props, 'runtime')
</script>

<template>
  <div class="grid gap-5">
    <section class="grid gap-3 border-b border-border pb-4 last:border-b-0 last:pb-0">
      <div class="grid gap-1">
        <h3 class="text-sm font-semibold text-text-primary">{{ t('settings.runtimeGroups.generation') }}</h3>
        <p class="text-sm text-text-secondary">{{ t('settings.runtimeGroupDescriptions.generation') }}</p>
      </div>
      <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <UiField :label="t('settings.fields.maxTokens')">
          <UiInput v-model="runtime.max_tokens" :placeholder="t('settings.placeholders.integerValue')" />
        </UiField>
        <UiField :label="t('settings.fields.temperature')">
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
        <UiField :label="t('settings.fields.maxSteps')">
          <UiInput v-model="runtime.max_steps" :placeholder="t('settings.placeholders.integerValue')" />
        </UiField>
        <UiField :label="t('settings.fields.maxSeconds')">
          <UiInput v-model="runtime.max_seconds" :placeholder="t('settings.placeholders.numberValue')" />
        </UiField>
        <UiField :label="t('settings.fields.interval')">
          <UiInput v-model="runtime.interval" :placeholder="t('settings.placeholders.numberValue')" />
        </UiField>
        <UiField :label="t('settings.fields.settleTimeout')" :hint="t('settings.fields.optional')">
          <UiInput v-model="runtime.settle_timeout" :placeholder="t('settings.placeholders.numberValue')" />
        </UiField>
      </div>
    </section>

    <section class="grid gap-3">
      <div class="grid gap-1">
        <h3 class="text-sm font-semibold text-text-primary">{{ t('settings.runtimeGroups.vision') }}</h3>
        <p class="text-sm text-text-secondary">{{ t('settings.runtimeGroupDescriptions.vision') }}</p>
      </div>
      <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <UiField :label="t('settings.fields.maxSide')">
          <UiInput v-model="runtime.max_side" :placeholder="t('settings.placeholders.integerValue')" />
        </UiField>
        <UiField :label="t('settings.fields.vlMaxSide')">
          <UiInput v-model="runtime.vl_max_side" :placeholder="t('settings.placeholders.integerValue')" />
        </UiField>
        <UiField :label="t('settings.fields.iconConf')">
          <UiInput v-model="runtime.icon_conf" :placeholder="t('settings.placeholders.numberValue')" />
        </UiField>
      </div>
    </section>
  </div>
</template>
