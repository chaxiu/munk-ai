<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

import { sidebarNavigationItems } from '@/app/shell/navigation'

const route = useRoute()
const { t } = useI18n()

const items = computed(() => sidebarNavigationItems.map((item) => ({
  ...item,
  label: t(item.labelKey),
})))
</script>

<template>
  <aside class="flex h-full flex-col gap-4 border-r border-border bg-surface-default px-3 py-4">
    <div class="flex items-center gap-3 px-2 py-1">
      <img
        src="/brand/logo-ui-40.png"
        alt="Munk AI logo"
        class="h-10 w-10 shrink-0 rounded-lg"
      >
      <div class="min-w-0">
        <strong class="block truncate text-base font-semibold text-text-primary">Munk AI</strong>
        <span class="block truncate text-xs font-medium uppercase tracking-[0.14em] text-text-tertiary">Local UI</span>
      </div>
    </div>

    <nav class="grid gap-1.5">
      <RouterLink
        v-for="item in items"
        :key="item.routeName"
        class="group relative flex min-h-9 items-center gap-3 overflow-hidden rounded-md px-3 text-sm font-medium text-text-secondary transition-all duration-150 hover:bg-surface-muted hover:text-text-primary"
        :class="{
          'bg-accent-soft text-text-primary shadow-sm': route.matched.some((record) => record.name === item.routeName),
        }"
        :to="{ name: item.routeName }"
      >
        <span
          class="absolute inset-y-1.5 left-1 w-1 rounded-full bg-accent transition-opacity duration-150"
          :class="route.matched.some((record) => record.name === item.routeName) ? 'opacity-100' : 'opacity-0 group-hover:opacity-60'"
        />
        <component :is="item.icon" class="h-4.5 w-4.5" />
        <span>{{ item.label }}</span>
      </RouterLink>
    </nav>
  </aside>
</template>
