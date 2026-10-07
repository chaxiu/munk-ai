<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

import AppSidebar from '@/app/shell/AppSidebar.vue'
import AppTopbar from '@/app/shell/AppTopbar.vue'
import { resolveShellActionComponent } from '@/app/shell/shellActionRegistry'

const route = useRoute()
const { t } = useI18n()

const pageTitle = computed(() => {
  if (typeof route.meta.navLabel === 'string') {
    return t(route.meta.navLabel as string)
  }
  if (typeof route.meta.title === 'string') {
    return route.meta.title as string
  }
  return t('app.title')
})
const shellActionComponent = computed(() => resolveShellActionComponent(route.meta.shellAction))
</script>

<template>
  <div class="grid min-h-screen bg-surface-muted lg:grid-cols-[280px_minmax(0,1fr)]">
    <AppSidebar />
    <div class="grid min-h-screen grid-rows-[auto_minmax(0,1fr)]">
      <AppTopbar>
        <h1 class="truncate text-xl font-semibold tracking-tight text-text-primary">{{ pageTitle }}</h1>
        <template #actions>
          <component :is="shellActionComponent" v-if="shellActionComponent" />
        </template>
      </AppTopbar>
      <main class="min-h-0 overflow-y-auto">
        <RouterView />
      </main>
    </div>
  </div>
</template>
