<script setup lang="ts">
import { PlusCircle } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import { knowledgeCardStatusTone } from '@/features/apps/knowledgePresentation'
import { summarizeKnowledgeCard } from '@/features/apps/knowledgeEditor'
import type { KnowledgeCard, KnowledgeCardStatus, KnowledgeCardType, KnowledgeSourceKind } from '@/shared/api/knowledge'
import AppBadge from '@/shared/components/AppBadge.vue'
import AppEmptyState from '@/shared/components/AppEmptyState.vue'
import { useTime } from '@/shared/time/useTime'
import UiButton from '@/shared/ui/UiButton.vue'
import UiInput from '@/shared/ui/UiInput.vue'
import UiSelect from '@/shared/ui/UiSelect.vue'

const props = defineProps<{
  cards: KnowledgeCard[]
  cardsErrorMessage: string | null
  isFetching: boolean
  selectedCardId: string | null
  isCreating: boolean
  queryFilter: string
  cardTypeFilter: KnowledgeCardType | ''
  statusFilter: KnowledgeCardStatus | ''
  cardTypeFilterOptions: Array<{ value: string, label: string }>
  statusFilterOptions: Array<{ value: string, label: string }>
}>()

defineEmits<{
  newCard: []
  selectCard: [cardId: string]
  'update:queryFilter': [value: string]
  'update:cardTypeFilter': [value: KnowledgeCardType | '']
  'update:statusFilter': [value: KnowledgeCardStatus | '']
}>()

const { t } = useI18n()
const time = useTime({ relative: true })

function typeLabel(type: KnowledgeCardType): string {
  return t(`apps.knowledge.cardTypes.${type}`)
}

function sourceLabel(kind: KnowledgeSourceKind): string {
  return t(`apps.knowledge.sources.${kind}`)
}

function cardStatusLabel(status: KnowledgeCardStatus): string {
  return t(`apps.knowledge.cardStatus.${status}`)
}
</script>

<template>
  <div class="flex h-full min-h-0 flex-col gap-3 rounded-2xl border border-border bg-surface-elevated p-4">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h3 class="text-base font-semibold text-text-primary">{{ $t('apps.knowledge.cardsTitle') }}</h3>
      </div>
      <UiButton type="button" size="sm" variant="primary" @click="$emit('newCard')">
        <PlusCircle class="h-4 w-4" />
        {{ $t('apps.knowledge.actions.newCard') }}
      </UiButton>
    </div>

    <div class="grid gap-3">
      <UiInput
        :model-value="props.queryFilter"
        :placeholder="$t('apps.knowledge.filters.queryPlaceholder')"
        @update:model-value="$emit('update:queryFilter', $event)"
      />
      <div class="grid gap-3 md:grid-cols-2">
        <UiSelect
          :model-value="props.cardTypeFilter"
          :options="props.cardTypeFilterOptions"
          :placeholder="$t('apps.knowledge.filters.allTypes')"
          @update:model-value="$emit('update:cardTypeFilter', $event as KnowledgeCardType | '')"
        />
        <UiSelect
          :model-value="props.statusFilter"
          :options="props.statusFilterOptions"
          :placeholder="$t('apps.knowledge.filters.allStatuses')"
          @update:model-value="$emit('update:statusFilter', $event as KnowledgeCardStatus | '')"
        />
      </div>
    </div>

    <AppEmptyState
      v-if="props.cardsErrorMessage"
      :title="$t('apps.knowledge.errorTitle')"
      :description="props.cardsErrorMessage"
    />

    <AppEmptyState
      v-else-if="!props.isFetching && props.cards.length === 0"
      :title="$t('apps.knowledge.cardsEmptyTitle')"
      :description="$t('apps.knowledge.cardsEmptyDescription')"
    >
      <template #actions>
        <UiButton type="button" variant="primary" @click="$emit('newCard')">
          <PlusCircle class="h-4 w-4" />
          {{ $t('apps.knowledge.actions.newCard') }}
        </UiButton>
      </template>
    </AppEmptyState>

    <div v-else class="min-h-0 flex-1 overflow-y-auto pr-1 scrollbar-subtle">
      <div class="grid gap-3">
        <button
          v-for="card in props.cards"
          :key="card.card_id"
          type="button"
          class="grid gap-2 rounded-xl border px-4 py-3 text-left transition-colors"
          :class="props.selectedCardId === card.card_id && !props.isCreating
            ? 'border-accent bg-accent/5'
            : 'border-border-muted bg-surface-muted hover:border-border-strong hover:bg-surface-default'"
          @click="$emit('selectCard', card.card_id)"
        >
          <div class="flex flex-wrap items-center gap-2">
            <p class="font-medium text-text-primary">{{ card.title }}</p>
            <AppBadge tone="neutral">{{ typeLabel(card.card_type) }}</AppBadge>
            <AppBadge :tone="knowledgeCardStatusTone(card.status)">{{ cardStatusLabel(card.status) }}</AppBadge>
          </div>
          <p v-if="summarizeKnowledgeCard(card)" class="text-sm text-text-secondary">{{ summarizeKnowledgeCard(card) }}</p>
          <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-text-muted">
            <span>{{ sourceLabel(card.source.kind) }}</span>
            <span>{{ $t('apps.knowledge.summary.confidence', { value: card.confidence.toFixed(2) }) }}</span>
            <time :datetime="time.datetime(card.updated_at) ?? undefined" :title="time.tooltip(card.updated_at)">
              {{ $t('apps.knowledge.summary.updatedAt', { value: time.relative(card.updated_at) }) }}
            </time>
          </div>
        </button>
      </div>
    </div>
  </div>
</template>
