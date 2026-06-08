<script setup lang="ts">
import { ArrowLeft, BookOpen, RefreshCcw, SquarePen } from '@lucide/vue'

import AppBadge from '@/shared/components/AppBadge.vue'
import AppCard from '@/shared/components/AppCard.vue'
import UiButton from '@/shared/ui/UiButton.vue'

defineProps<{
  platform: string
  displayAppName: string
  appId: string
  pendingCandidateLabel: string
}>()

defineEmits<{
  refresh: []
  openApp: []
  openCandidates: []
  back: []
}>()
</script>

<template>
  <AppCard class="grid gap-3">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div class="grid gap-1">
        <div class="flex flex-wrap items-center gap-2">
          <h2 class="text-lg font-semibold text-text-primary">{{ $t('apps.knowledge.title') }}</h2>
          <AppBadge tone="neutral">{{ platform }}</AppBadge>
        </div>
        <p class="text-sm text-text-secondary">{{ displayAppName }} / {{ appId }}</p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <UiButton type="button" variant="secondary" @click="$emit('openCandidates')">
          <BookOpen class="h-4 w-4" />
          {{ $t('apps.knowledge.actions.openCandidates') }}
          <span class="rounded-full bg-surface-muted px-2 py-0.5 text-xs text-text-secondary">
            {{ pendingCandidateLabel }}
          </span>
        </UiButton>
        <UiButton type="button" variant="secondary" @click="$emit('refresh')">
          <RefreshCcw class="h-4 w-4" />
          {{ $t('common.refresh') }}
        </UiButton>
        <UiButton type="button" variant="secondary" @click="$emit('openApp')">
          <SquarePen class="h-4 w-4" />
          {{ $t('apps.knowledge.actions.openApp') }}
        </UiButton>
        <UiButton type="button" variant="ghost" @click="$emit('back')">
          <ArrowLeft class="h-4 w-4" />
          {{ $t('apps.knowledge.actions.backToApps') }}
        </UiButton>
      </div>
    </div>
  </AppCard>
</template>
