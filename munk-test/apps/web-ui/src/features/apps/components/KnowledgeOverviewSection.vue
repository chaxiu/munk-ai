<script setup lang="ts">
import { useI18n } from 'vue-i18n'

import type { KnowledgeDocumentSummary } from '@/features/apps/knowledgePresentation'
import type { KnowledgeCardType } from '@/shared/api/knowledge'
import AppBadge from '@/shared/components/AppBadge.vue'
import AppEmptyState from '@/shared/components/AppEmptyState.vue'

const props = defineProps<{
  appKnowledgeExists: boolean
  knowledgeRef: string | null | undefined
  summary: KnowledgeDocumentSummary | null
}>()

const { t } = useI18n()

function typeLabel(type: KnowledgeCardType | 'unknown'): string {
  if (type === 'unknown') {
    return t('apps.knowledge.cardTypes.unknown')
  }
  return t(`apps.knowledge.cardTypes.${type}`)
}
</script>

<template>
  <section class="grid gap-4">
    <div class="grid gap-1">
      <h3 class="text-base font-semibold text-text-primary">{{ $t('apps.knowledge.overviewTitle') }}</h3>
      <p class="text-sm text-text-secondary">{{ $t('apps.knowledge.overviewDescription') }}</p>
    </div>

    <AppEmptyState
      v-if="!props.appKnowledgeExists || !props.summary"
      :title="$t('apps.knowledge.emptyTitle')"
      :description="$t('apps.knowledge.emptyDescription')"
    />

    <div v-else class="grid gap-4 rounded-2xl border border-border bg-surface-elevated p-4">
      <dl class="grid gap-3 md:grid-cols-4">
        <div class="grid gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
          <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ $t('apps.knowledge.fields.fileName') }}</dt>
          <dd class="break-all text-sm text-text-primary">{{ props.knowledgeRef ?? 'app_knowledge.json' }}</dd>
        </div>
        <div class="grid gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
          <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ $t('apps.knowledge.fields.schemaVersion') }}</dt>
          <dd class="text-sm text-text-primary">{{ props.summary.schemaVersion }}</dd>
        </div>
        <div class="grid gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
          <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ $t('apps.knowledge.fields.documentAppId') }}</dt>
          <dd class="text-sm text-text-primary">{{ props.summary.appId }}</dd>
        </div>
        <div class="grid gap-1 rounded-xl border border-border-muted bg-surface-muted p-4">
          <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ $t('apps.knowledge.fields.cardCount') }}</dt>
          <dd class="text-sm text-text-primary">{{ props.summary.cardCount }}</dd>
        </div>
      </dl>

      <div class="grid gap-2">
        <p class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ $t('apps.knowledge.fields.cardTypes') }}</p>
        <div class="flex flex-wrap gap-2">
          <AppBadge v-for="item in props.summary.typeCounts" :key="item.type" tone="neutral">
            {{ typeLabel(item.type) }} · {{ item.count }}
          </AppBadge>
        </div>
      </div>
    </div>
  </section>
</template>
