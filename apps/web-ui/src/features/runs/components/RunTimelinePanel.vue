<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import AppEmptyState from '@/shared/components/AppEmptyState.vue'
import { presentRunTimelineEvent } from '@/features/runs/lib/runMappers'
import type { OperationEventsData } from '@/shared/api/operations'

type TimePresenter = {
  absolute: (value: string | null | undefined) => string
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
const expandedLlmItems = ref<Set<number>>(new Set())
const expandedSetupSections = ref<Set<string>>(new Set())
const overflowingLlmItems = ref<Set<number>>(new Set())
const llmContentElements = new Map<number, HTMLElement>()
const llmSeqByElement = new WeakMap<HTMLElement, number>()
const LLM_COLLAPSED_MAX_HEIGHT_EM = 15.6
let llmResizeObserver: ResizeObserver | null = null
let pendingMeasureFrame: number | null = null
const pendingMeasureSeqs = new Set<number>()

const presentedItems = computed(() => props.items.map((item) => ({
  ...item,
  presentation: presentRunTimelineEvent(item, t),
})))

function isLlmExpanded(seq: number): boolean {
  return expandedLlmItems.value.has(seq)
}

function toggleLlmExpanded(seq: number) {
  const next = new Set(expandedLlmItems.value)
  if (next.has(seq)) {
    next.delete(seq)
  } else {
    next.add(seq)
  }
  expandedLlmItems.value = next
}

function isLlmOverflowing(seq: number): boolean {
  return overflowingLlmItems.value.has(seq)
}

function updateOverflowingState(seq: number, isOverflowing: boolean) {
  const hadValue = overflowingLlmItems.value.has(seq)
  if (hadValue === isOverflowing) {
    return
  }
  const next = new Set(overflowingLlmItems.value)
  if (isOverflowing) {
    next.add(seq)
  } else {
    next.delete(seq)
  }
  overflowingLlmItems.value = next
}

function measureLlmOverflow(seq: number) {
  const element = llmContentElements.get(seq)
  if (!element || typeof window === 'undefined') {
    updateOverflowingState(seq, false)
    return
  }
  const computedStyle = window.getComputedStyle(element)
  const fontSize = Number.parseFloat(computedStyle.fontSize) || 13
  const collapsedMaxHeight = fontSize * LLM_COLLAPSED_MAX_HEIGHT_EM
  updateOverflowingState(seq, element.scrollHeight > collapsedMaxHeight + 1)
}

function scheduleMeasureLlmOverflow(seq?: number) {
  if (typeof window === 'undefined') {
    return
  }
  if (seq != null) {
    pendingMeasureSeqs.add(seq)
  } else {
    for (const key of llmContentElements.keys()) {
      pendingMeasureSeqs.add(key)
    }
  }
  if (pendingMeasureFrame != null) {
    return
  }
  pendingMeasureFrame = window.requestAnimationFrame(() => {
    pendingMeasureFrame = null
    const seqs = [...pendingMeasureSeqs]
    pendingMeasureSeqs.clear()
    for (const key of seqs) {
      measureLlmOverflow(key)
    }
  })
}

function setLlmContentRef(seq: number, element: Element | null) {
  const current = element instanceof HTMLElement ? element : null
  const previous = llmContentElements.get(seq)
  if (previous === current) {
    return
  }
  if (previous && previous !== current) {
    llmResizeObserver?.unobserve(previous)
    llmContentElements.delete(seq)
    updateOverflowingState(seq, false)
  }
  if (!current) {
    return
  }
  llmContentElements.set(seq, current)
  llmSeqByElement.set(current, seq)
  llmResizeObserver?.observe(current)
  scheduleMeasureLlmOverflow(seq)
}

function shouldShowLlmToggle(item: OperationEventItem & { presentation: ReturnType<typeof presentRunTimelineEvent> }): boolean {
  const previewText = item.presentation.llmPreviewText ?? null
  const fullText = item.presentation.llmFullText ?? null
  return (previewText != null && fullText != null && previewText !== fullText) || isLlmOverflowing(item.seq)
}

function setupSectionKey(seq: number, sectionId: string): string {
  return `${seq}:${sectionId}`
}

function isSetupSectionExpanded(seq: number, sectionId: string): boolean {
  return expandedSetupSections.value.has(setupSectionKey(seq, sectionId))
}

function toggleSetupSectionExpanded(seq: number, sectionId: string) {
  const key = setupSectionKey(seq, sectionId)
  const next = new Set(expandedSetupSections.value)
  if (next.has(key)) {
    next.delete(key)
  } else {
    next.add(key)
  }
  expandedSetupSections.value = next
}

function shouldShowSetupSectionToggle(section: { previewText: string; fullText: string }): boolean {
  return section.previewText !== section.fullText
}

watch(
  presentedItems,
  (items) => {
    const next = new Set(expandedSetupSections.value)
    let changed = false
    for (const item of items) {
      for (const sectionId of item.presentation.defaultExpandedSectionIds ?? []) {
        const key = setupSectionKey(item.seq, sectionId)
        if (!next.has(key)) {
          next.add(key)
          changed = true
        }
      }
    }
    if (changed) {
      expandedSetupSections.value = next
    }
  },
  { immediate: true },
)

onMounted(() => {
  if (typeof ResizeObserver !== 'undefined') {
    llmResizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const seq = llmSeqByElement.get(entry.target as HTMLElement)
        if (seq != null) {
          measureLlmOverflow(seq)
        }
      }
    })
    for (const [seq, element] of llmContentElements.entries()) {
      llmResizeObserver.observe(element)
      measureLlmOverflow(seq)
    }
  } else if (typeof window !== 'undefined') {
    window.addEventListener('resize', handleWindowResize)
    scheduleMeasureLlmOverflow()
  }
})

onBeforeUnmount(() => {
  llmResizeObserver?.disconnect()
  llmResizeObserver = null
  if (typeof window !== 'undefined') {
    window.removeEventListener('resize', handleWindowResize)
    if (pendingMeasureFrame != null) {
      window.cancelAnimationFrame(pendingMeasureFrame)
      pendingMeasureFrame = null
    }
  }
})

function handleWindowResize() {
  scheduleMeasureLlmOverflow()
}
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
      :class="[
        `event-row--${item.presentation.category}`,
        { 'event-row--llm': item.presentation.kind === 'llm' },
        { 'event-row--setup': item.presentation.kind === 'setup_step' },
        { 'event-row--start-state': item.presentation.kind === 'start_state_step' },
        { 'event-row--failed': item.presentation.failed === true },
        { 'event-row--skipped': item.presentation.skipped === true },
      ]"
    >
      <div class="event-top">
        <strong>{{ item.presentation.title }}</strong>
        <time
          class="event-time"
          :datetime="time.datetime(item.timestamp) ?? undefined"
          :title="time.tooltip(item.timestamp) ?? undefined"
        >
          {{ time.absolute(item.timestamp) }}
        </time>
        <span class="muted event-seq">#{{ item.seq }}</span>
      </div>
      <template v-if="item.presentation.kind === 'llm'">
        <p v-if="item.presentation.description" class="event-description">{{ item.presentation.description }}</p>
        <section class="llm-panel">
          <pre
            v-if="item.presentation.llmFullText || item.presentation.llmPreviewText"
            :ref="(element) => setLlmContentRef(item.seq, element as Element | null)"
            class="llm-content"
            :class="{ 'llm-content--expanded': isLlmExpanded(item.seq) }"
          >{{ isLlmExpanded(item.seq) ? item.presentation.llmFullText : item.presentation.llmPreviewText }}</pre>
          <p v-else class="event-description">{{ t('runDetail.timeline.llm.emptyText') }}</p>
          <div v-if="shouldShowLlmToggle(item)" class="llm-panel-footer">
            <button
              type="button"
              class="llm-toggle"
              :aria-expanded="isLlmExpanded(item.seq)"
              @click="toggleLlmExpanded(item.seq)"
            >
              {{ isLlmExpanded(item.seq) ? t('runDetail.timeline.llm.showLess') : t('runDetail.timeline.llm.showMore') }}
            </button>
          </div>
        </section>
      </template>
      <template v-else-if="item.presentation.kind === 'setup_step'">
        <p v-if="item.presentation.description" class="event-description">{{ item.presentation.description }}</p>
        <section
          v-for="section in item.presentation.setupSections ?? []"
          :key="`${item.seq}-${section.id}`"
          class="setup-panel"
        >
          <div class="setup-panel-header muted">{{ section.label }}</div>
          <pre
            class="setup-content"
            :class="{ 'setup-content--expanded': isSetupSectionExpanded(item.seq, section.id) }"
          >{{ isSetupSectionExpanded(item.seq, section.id) ? section.fullText : section.previewText }}</pre>
          <div v-if="shouldShowSetupSectionToggle(section)" class="setup-panel-footer">
            <button
              type="button"
              class="setup-toggle"
              :aria-expanded="isSetupSectionExpanded(item.seq, section.id)"
              @click="toggleSetupSectionExpanded(item.seq, section.id)"
            >
              {{
                isSetupSectionExpanded(item.seq, section.id)
                  ? t('runDetail.timeline.setup.showLess')
                  : t('runDetail.timeline.setup.showMore')
              }}
            </button>
          </div>
        </section>
        <details v-if="item.presentation.rawData || item.presentation.eventTypeLabel" class="event-debug">
          <summary>{{ t('runDetail.timeline.debug.title') }}</summary>
          <div class="event-debug-body">
            <div class="event-debug-row">
              <span class="muted">{{ t('runDetail.timeline.debug.eventType') }}</span>
              <code>{{ item.presentation.eventTypeLabel }}</code>
            </div>
            <div v-if="item.presentation.rawData" class="event-debug-row event-debug-row--stacked">
              <span class="muted">{{ t('runDetail.timeline.debug.dataJson') }}</span>
              <pre>{{ JSON.stringify(item.presentation.rawData, null, 2) }}</pre>
            </div>
          </div>
        </details>
      </template>
      <template v-else-if="item.presentation.kind === 'start_state_step'">
        <p v-if="item.presentation.description" class="event-description">{{ item.presentation.description }}</p>
        <section
          v-for="section in item.presentation.startStateSections ?? []"
          :key="`${item.seq}-${section.id}`"
          class="setup-panel"
        >
          <div class="setup-panel-header muted">{{ section.label }}</div>
          <pre
            class="setup-content"
            :class="{ 'setup-content--expanded': isSetupSectionExpanded(item.seq, section.id) }"
          >{{ isSetupSectionExpanded(item.seq, section.id) ? section.fullText : section.previewText }}</pre>
          <div v-if="shouldShowSetupSectionToggle(section)" class="setup-panel-footer">
            <button
              type="button"
              class="setup-toggle"
              :aria-expanded="isSetupSectionExpanded(item.seq, section.id)"
              @click="toggleSetupSectionExpanded(item.seq, section.id)"
            >
              {{
                isSetupSectionExpanded(item.seq, section.id)
                  ? t('runDetail.timeline.startState.showLess')
                  : t('runDetail.timeline.startState.showMore')
              }}
            </button>
          </div>
        </section>
        <details v-if="item.presentation.rawData || item.presentation.eventTypeLabel" class="event-debug">
          <summary>{{ t('runDetail.timeline.debug.title') }}</summary>
          <div class="event-debug-body">
            <div class="event-debug-row">
              <span class="muted">{{ t('runDetail.timeline.debug.eventType') }}</span>
              <code>{{ item.presentation.eventTypeLabel }}</code>
            </div>
            <div v-if="item.presentation.rawData" class="event-debug-row event-debug-row--stacked">
              <span class="muted">{{ t('runDetail.timeline.debug.dataJson') }}</span>
              <pre>{{ JSON.stringify(item.presentation.rawData, null, 2) }}</pre>
            </div>
          </div>
        </details>
      </template>
      <template v-else>
        <p v-if="item.presentation.description" class="event-description">{{ item.presentation.description }}</p>
        <dl v-if="item.presentation.detailRows.length > 0" class="event-details">
          <template v-for="(row, rowIndex) in item.presentation.detailRows" :key="`${item.seq}-${row.label}-${rowIndex}`">
            <dt class="muted">{{ row.label }}</dt>
            <dd>{{ row.value }}</dd>
          </template>
        </dl>
        <details v-if="item.presentation.rawData || item.presentation.eventTypeLabel" class="event-debug">
          <summary>{{ t('runDetail.timeline.debug.title') }}</summary>
          <div class="event-debug-body">
            <div class="event-debug-row">
              <span class="muted">{{ t('runDetail.timeline.debug.eventType') }}</span>
              <code>{{ item.presentation.eventTypeLabel }}</code>
            </div>
            <div v-if="item.presentation.rawData" class="event-debug-row event-debug-row--stacked">
              <span class="muted">{{ t('runDetail.timeline.debug.dataJson') }}</span>
              <pre>{{ JSON.stringify(item.presentation.rawData, null, 2) }}</pre>
            </div>
          </div>
        </details>
      </template>
    </article>
  </div>
</template>

<style scoped>
.event-list,
.event-row,
.event-debug-body {
  display: grid;
  gap: 12px;
}

.muted {
  color: var(--text-secondary);
}

.event-row,
.event-top {
  display: grid;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid var(--border-muted);
}

.event-row--orchestration {
  border-top-color: var(--accent-primary);
}

.event-row--llm {
  border-top-color: var(--accent-secondary, var(--accent-primary));
}

.event-row--setup {
  border-top-color: color-mix(in srgb, var(--accent-primary) 70%, var(--border-muted));
}

.event-row--start-state {
  border-top-color: color-mix(in srgb, var(--accent-secondary, var(--accent-primary)) 55%, var(--border-muted));
}

.event-row--failed strong {
  color: var(--status-danger, #c62828);
}

.event-row--skipped strong,
.event-row--skipped .event-description {
  color: var(--text-secondary);
}

.setup-panel {
  display: grid;
  gap: 8px;
  padding: 14px;
  border: 1px solid color-mix(in srgb, var(--accent-primary) 18%, var(--border-default));
  border-radius: 14px;
  background: var(--surface-subtle);
}

.setup-panel-header {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.setup-content {
  margin: 0;
  padding: 2px 0;
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
  line-height: 1.6;
  font-size: 13px;
}

.setup-content:not(.setup-content--expanded) {
  max-height: 15.6em;
  overflow: hidden;
  mask-image: linear-gradient(180deg, #000 0%, #000 78%, transparent 100%);
}

.setup-panel-footer {
  display: flex;
  justify-content: flex-start;
}

.setup-toggle {
  min-height: 30px;
  padding: 0 10px;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--accent-primary) 30%, var(--border-default));
  background: color-mix(in srgb, var(--surface-default) 82%, var(--accent-primary) 18%);
  color: var(--accent-primary);
  font: inherit;
  font-size: 12px;
  font-weight: 600;
  line-height: 1;
  cursor: pointer;
}

.setup-toggle:focus-visible {
  outline: 2px solid color-mix(in srgb, var(--accent-primary) 55%, transparent);
  outline-offset: 2px;
}

.event-top,
.event-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.event-top {
  justify-content: space-between;
}

.event-top strong {
  flex: 1 1 auto;
  min-width: 0;
}

.event-time {
  margin-left: auto;
  white-space: nowrap;
  color: var(--text-secondary);
  font-size: 13px;
}

.event-seq {
  white-space: nowrap;
}

.event-description {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.5;
}

.event-details {
  display: grid;
  grid-template-columns: minmax(120px, 180px) minmax(0, 1fr);
  gap: 8px 12px;
  margin: 0;
  padding: 12px 14px;
  border: 1px solid var(--border-muted);
  border-radius: 12px;
  background: var(--surface-subtle);
}

.event-details dt,
.event-details dd {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
}

.event-details dd {
  word-break: break-word;
  overflow-wrap: anywhere;
}

.llm-panel {
  display: grid;
  gap: 10px;
  padding: 14px;
  border: 1px solid color-mix(in srgb, var(--accent-secondary, var(--accent-primary)) 18%, var(--border-default));
  border-radius: 14px;
  background:
    linear-gradient(
      180deg,
      color-mix(in srgb, var(--accent-secondary, var(--accent-primary)) 6%, var(--surface-subtle)) 0%,
      var(--surface-subtle) 100%
    );
}

.llm-content {
  margin: 0;
  padding: 2px 0;
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
  line-height: 1.6;
  font-size: 13px;
}

.llm-content:not(.llm-content--expanded) {
  max-height: 15.6em;
  overflow: hidden;
  mask-image: linear-gradient(180deg, #000 0%, #000 78%, transparent 100%);
}

.llm-panel-footer {
  display: flex;
  justify-content: flex-start;
}

.llm-toggle {
  min-height: 30px;
  padding: 0 10px;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--accent-secondary, var(--accent-primary)) 30%, var(--border-default));
  background: color-mix(in srgb, var(--surface-default) 82%, var(--accent-secondary, var(--accent-primary)) 18%);
  color: var(--accent-secondary, var(--accent-primary));
  font: inherit;
  font-size: 12px;
  font-weight: 600;
  line-height: 1;
  cursor: pointer;
  transition: background-color 140ms ease, border-color 140ms ease, transform 140ms ease;
}

.llm-toggle:hover {
  background: color-mix(in srgb, var(--surface-default) 68%, var(--accent-secondary, var(--accent-primary)) 32%);
  border-color: color-mix(in srgb, var(--accent-secondary, var(--accent-primary)) 50%, var(--border-default));
}

.llm-toggle:focus-visible {
  outline: 2px solid color-mix(in srgb, var(--accent-secondary, var(--accent-primary)) 55%, transparent);
  outline-offset: 2px;
}

.llm-toggle:active {
  transform: translateY(1px);
}

.event-debug {
  display: grid;
  gap: 8px;
}

.event-debug summary {
  cursor: pointer;
  color: var(--text-secondary);
}

.event-debug-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.event-debug-row--stacked {
  display: grid;
  justify-content: stretch;
}

pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
  max-width: 100%;
  overflow-x: auto;
  align-items: center;
}

code {
  word-break: break-word;
}
</style>
