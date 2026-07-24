<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import CloudAuthCard from '@/features/cloud/components/CloudAuthCard.vue'
import CloudSyncCard from '@/features/cloud/components/CloudSyncCard.vue'
import { useCloudAuthSessionQuery } from '@/features/cloud/queries/useCloudAuthSessionQuery'

const { t } = useI18n()
const sessionQuery = useCloudAuthSessionQuery()
const authenticated = computed(() => Boolean(sessionQuery.data.value?.authenticated))
</script>

<template>
  <section class="app-page max-w-4xl">
    <div class="mb-4 grid gap-1">
      <h1 class="text-2xl font-semibold text-text-primary">{{ t('cloud.title') }}</h1>
      <p class="text-sm text-text-secondary">{{ t('cloud.description') }}</p>
    </div>

    <div class="grid gap-4">
      <CloudAuthCard />
      <CloudSyncCard :authenticated="authenticated" />
    </div>
  </section>
</template>
