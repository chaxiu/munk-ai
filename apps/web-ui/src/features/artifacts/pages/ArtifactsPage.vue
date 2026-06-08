<script setup lang="ts">
import { useI18n } from 'vue-i18n'

import AppEmptyState from '@/shared/components/AppEmptyState.vue'

const { t } = useI18n()
</script>

<template>
  <AppEmptyState :title="t('nav.devices')" :description="t('placeholders.artifacts')" />
</template>
