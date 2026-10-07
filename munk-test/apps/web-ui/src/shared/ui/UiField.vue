<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

import UiInfoPopover from '@/shared/ui/UiInfoPopover.vue'

defineOptions({
  inheritAttrs: false,
})

const props = defineProps<{
  label: string
  hint?: string
  error?: string | null
  required?: boolean
  optional?: boolean
  description?: string
}>()

const { t } = useI18n()
const isHeaderHovered = ref(false)
</script>

<template>
  <div class="grid gap-2.5" v-bind="$attrs">
    <div class="flex items-start justify-between gap-3">
      <div
        class="flex min-w-0 flex-wrap items-center gap-2"
        @mouseenter="isHeaderHovered = true"
        @mouseleave="isHeaderHovered = false"
      >
        <span class="text-sm font-medium text-text-primary">{{ label }}</span>
        <span
          v-if="props.required"
          class="inline-flex items-center rounded-full border border-error/15 bg-error/5 px-2 py-0.5 text-[11px] font-medium text-error-text"
        >
          {{ t('settings.fields.required') }}
        </span>
        <span
          v-else-if="props.optional"
          class="inline-flex items-center rounded-full border border-border bg-surface-muted/45 px-2 py-0.5 text-[11px] font-medium text-text-muted"
        >
          {{ t('settings.fields.optional') }}
        </span>
        <UiInfoPopover
          v-if="props.description"
          :label="label"
          :description="props.description"
          :force-open="isHeaderHovered"
        />
      </div>
      <span v-if="hint && !error" class="pt-0.5 text-xs text-text-muted">{{ hint }}</span>
    </div>
    <slot />
    <p v-if="error" class="text-sm text-error-text">{{ error }}</p>
  </div>
</template>
