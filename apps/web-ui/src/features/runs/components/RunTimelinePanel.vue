<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import AppEmptyState from '@/shared/components/AppEmptyState.vue'
import { presentRunTimelineEvent } from '@/features/runs/lib/runMappers'
import type { OperationEventsData } from '@/shared/api/operations'

type TimePresenter = {
  datetime: (value: string | null | undefined) => string | null
  tooltip: (value: string | null | undefined) => string | null
  relative: (value: string | null | undefined) => string
}

type OperationEventItem = NonNullable<OperationEventsData['items']>[number]

const props = defineProps<{
  items: OperationEventItem[]
  time: TimePresenter
}>()

const { t } = useI18n()

const presentedItems = computed(() => props.items.map((item) => ({
  ...item,
  presentation: presentRunTimelineEvent(item, t),
})))
</script>

<template>
  <AppEmptyState
    v-if="props.items.length === 0"
    :title="t('runDetail.timeline.emptyTitle')"
    :description="t('runDetail.timeline.emptyDescription')"
  />
  <div v-else class="event-list">
    <article
      v-for="item in presentedItems"
      :key="item.seq"
      class="event-row"
      :class="`event-row--${item.presentation.category}`"
    >
      <div class="event-top">
        <strong>{{ item.presentation.title }}</strong>
        <span class="muted">#{{ item.seq }}</span>
      </div>
      <div class="event-meta">
        <span>{{ item.presentation.categoryLabel }} · {{ item.event_type }}</span>
        <time
          :datetime="time.datetime(item.timestamp) ?? undefined"
          :title="time.tooltip(item.timestamp) ?? undefined"
        >
          {{ time.relative(item.timestamp) }}
        </time>
      </div>
      <p v-if="item.presentation.description" class="event-description">{{ item.presentation.description }}</p>
      <pre v-if="item.data_json">{{ JSON.stringify(item.data_json, null, 2) }}</pre>
    </article>
  </div>
</template>

<style scoped>
.event-list,
.event-row {
  display: grid;
  gap: 12px;
}

.muted,
.event-meta {
  color: var(--text-secondary);
}

.event-row,
.event-top,
.event-meta {
  display: grid;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid var(--border-muted);
}

.event-row--orchestration {
  border-top-color: var(--accent-primary);
}

.event-top,
.event-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.event-description {
  margin: 0;
  color: var(--text-secondary);
}

pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
  overflow-x: auto;
  max-width: 100%;
}
</style>
