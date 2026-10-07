<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { useAppKnowledgeCandidatesQuery } from '@/features/apps/queries/useAppKnowledgeCandidatesQuery'
import type { KnowledgePostActionResultView } from '@/features/runs/lib/runSummaryMappers'

const props = defineProps<{
  appId: string | null | undefined
  result: KnowledgePostActionResultView
}>()

const { t } = useI18n()

const shouldLookupCandidate = computed(() => (
  props.result.submitted
  && Boolean(props.result.candidateId)
  && Boolean(props.appId)
))

const candidatesQuery = useAppKnowledgeCandidatesQuery(computed(() => ({
  appId: props.appId,
})))

const matchedCandidate = computed(() => {
  if (!shouldLookupCandidate.value || !props.result.candidateId) {
    return null
  }
  const items = candidatesQuery.data.value?.items ?? []
  return items.find((item) => item.candidate_id === props.result.candidateId) ?? null
})

const approvalHref = computed(() => {
  if (!props.appId || !props.result.candidateId) {
    return null
  }
  const params = new URLSearchParams({ candidate_id: props.result.candidateId })
  return `/apps/${encodeURIComponent(props.appId)}/knowledge/candidates?${params.toString()}`
})

const showReviewAction = computed(() => (
  shouldLookupCandidate.value
  && matchedCandidate.value?.status === 'pending_review'
  && approvalHref.value != null
))

const showViewCandidateAction = computed(() => (
  shouldLookupCandidate.value
  && matchedCandidate.value != null
  && matchedCandidate.value.status !== 'pending_review'
  && approvalHref.value != null
))

function skipReasonLabel(skipReason: string | null): string {
  if (!skipReason) {
    return '-'
  }
  const key = `runDetail.knowledge.skipReasons.${skipReason}`
  const translated = t(key)
  return translated === key ? skipReason : translated
}
</script>

<template>
  <section class="knowledge-card">
    <div class="knowledge-head">
      <strong>{{ t('runDetail.knowledge.title') }}</strong>
      <span class="knowledge-badge" :class="{ submitted: result.submitted, skipped: !result.submitted }">
        {{ result.submitted ? t('runDetail.knowledge.submitted') : t('runDetail.knowledge.skipped') }}
      </span>
    </div>
    <div class="knowledge-grid">
      <div class="knowledge-item knowledge-item-full">
        <span class="knowledge-label">{{ t('runDetail.knowledge.fields.summary') }}</span>
        <strong>{{ result.summary || '-' }}</strong>
      </div>
      <div v-if="!result.submitted" class="knowledge-item">
        <span class="knowledge-label">{{ t('runDetail.knowledge.fields.skipReason') }}</span>
        <strong>{{ skipReasonLabel(result.skipReason) }}</strong>
      </div>
      <div v-if="result.candidateId" class="knowledge-item">
        <span class="knowledge-label">{{ t('runDetail.knowledge.fields.candidateId') }}</span>
        <strong class="break-all">{{ result.candidateId }}</strong>
      </div>
    </div>
    <div v-if="showReviewAction || showViewCandidateAction" class="knowledge-actions">
      <a class="secondary-link" :href="approvalHref ?? undefined">
        {{
          showReviewAction
            ? t('runDetail.knowledge.actions.review')
            : t('runDetail.knowledge.actions.viewCandidate')
        }}
      </a>
    </div>
  </section>
</template>

<style scoped>
.knowledge-card,
.knowledge-grid,
.knowledge-actions {
  display: grid;
  gap: 12px;
}

.knowledge-card {
  padding: 16px;
  border-radius: 12px;
  border: 1px solid var(--border-muted);
  background: var(--surface-subtle);
}

.knowledge-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.knowledge-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.knowledge-item {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.knowledge-item-full {
  grid-column: 1 / -1;
}

.knowledge-label {
  color: var(--text-secondary);
}

.knowledge-badge {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 0.82rem;
}

.knowledge-badge.submitted {
  color: var(--status-success-text);
  background: var(--status-success-bg);
}

.knowledge-badge.skipped {
  color: var(--status-warning-text);
  background: var(--status-warning-bg);
}

.secondary-link {
  min-height: 38px;
  padding: 0 14px;
  border-radius: 8px;
  font: inherit;
  border: 1px solid var(--border-default);
  background: var(--surface-default);
  color: var(--text-primary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: fit-content;
}

@media (max-width: 880px) {
  .knowledge-grid {
    grid-template-columns: 1fr;
  }
}
</style>
