<script setup lang="ts">
import AppCard from '@/shared/components/AppCard.vue'
import AppEmptyState from '@/shared/components/AppEmptyState.vue'
</script>

<template>
  <section class="app-page box-border">
    <AppCard>
      <AppEmptyState
        :title="$t('notFound.title')"
        :description="$t('notFound.description')"
      >
        <template #actions>
          <RouterLink class="inline-flex min-h-9 items-center justify-center rounded-md border border-accent bg-accent px-4 text-sm font-medium text-white shadow-sm transition-colors hover:border-accent-strong hover:bg-accent-strong" to="/">
            {{ $t('notFound.goHome') }}
          </RouterLink>
        </template>
      </AppEmptyState>
    </AppCard>
  </section>
</template>
