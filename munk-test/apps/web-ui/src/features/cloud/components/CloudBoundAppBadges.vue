<script setup lang="ts">
import { useI18n } from 'vue-i18n'

import AppBadge from '@/shared/components/AppBadge.vue'

withDefaults(defineProps<{
  bound?: boolean
  dirty?: boolean
}>(), {
  bound: false,
  dirty: false,
})

const { t } = useI18n()
</script>

<template>
  <span v-if="bound" class="inline-flex flex-wrap items-center gap-1.5">
    <AppBadge tone="success">{{ t('cloud.marker.bound') }}</AppBadge>
    <AppBadge v-if="dirty" tone="warning">{{ t('cloud.marker.dirty') }}</AppBadge>
  </span>
</template>
