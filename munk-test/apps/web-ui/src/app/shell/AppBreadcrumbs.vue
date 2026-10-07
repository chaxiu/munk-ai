<script setup lang="ts">
import { ChevronRight } from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

const route = useRoute()
const { t } = useI18n()

const crumbs = computed(() => route.matched
  .filter((record) => typeof record.meta.navLabel === 'string')
  .map((record) => ({
    path: record.path,
    label: t(record.meta.navLabel as string),
  }))
  .slice(0, -1))
</script>

<template>
  <nav v-if="crumbs.length > 0" class="flex flex-wrap items-center gap-2 text-sm text-text-muted" aria-label="breadcrumbs">
    <span v-for="(crumb, index) in crumbs" :key="crumb.path" class="flex items-center gap-2">
      <span class="transition-colors hover:text-text-secondary">{{ crumb.label }}</span>
      <ChevronRight v-if="index < crumbs.length - 1" class="h-3.5 w-3.5" />
    </span>
  </nav>
</template>
