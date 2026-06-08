<script setup lang="ts">
import { ArrowLeft, Check, RefreshCcw, SquarePen, X } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import { summarizeKnowledgeCandidate } from '@/features/apps/knowledgeEditor'
import { useAppDetailQuery } from '@/features/apps/queries/useAppDetailQuery'
import { useAppKnowledgeCandidatesQuery } from '@/features/apps/queries/useAppKnowledgeCandidatesQuery'
import { useKnowledgeCandidateMutations } from '@/features/apps/queries/useKnowledgeCandidateMutations'
import { LocalApiClientError } from '@/shared/api/client'
import type { KnowledgeCandidateRecord, KnowledgeCandidateStatus, KnowledgeCardType, KnowledgeSourceKind } from '@/shared/api/knowledge'
import AppBadge from '@/shared/components/AppBadge.vue'
import AppCard from '@/shared/components/AppCard.vue'
import AppEmptyState from '@/shared/components/AppEmptyState.vue'
import { translateErrorCode } from '@/shared/i18n/errorMessages'
import { useTime } from '@/shared/time/useTime'
import UiButton from '@/shared/ui/UiButton.vue'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const time = useTime({ relative: true })
const candidateMutations = useKnowledgeCandidateMutations()
const actionError = ref<string | null>(null)
const actionMessage = ref<string | null>(null)

const appId = computed(() => {
  const value = route.params.appId
  return typeof value === 'string' ? value : null
})

const appDetailQuery = useAppDetailQuery(appId)
const candidatesQuery = useAppKnowledgeCandidatesQuery(computed(() => ({
  appId: appId.value,
})))

const detail = computed(() => appDetailQuery.data.value)
const displayAppName = computed(() => {
  const profile = detail.value?.profile
  if (!profile) {
    return appId.value ?? '-'
  }
  return profile.app_name?.trim() || profile.app_id
})
const candidates = computed(() => candidatesQuery.data.value?.items ?? [])
const pendingCandidates = computed(() => candidates.value.filter(item => item.status === 'pending_review'))
const approvedCandidates = computed(() => candidates.value.filter(item => item.status === 'approved'))
const rejectedCandidates = computed(() => candidates.value.filter(item => item.status === 'rejected'))
const pageErrorMessage = computed(() => translateUnknownError(appDetailQuery.error.value))
const candidatesErrorMessage = computed(() => translateUnknownError(candidatesQuery.error.value))
const busyCandidateId = computed(() => candidateMutations.approveCandidate.variables.value?.candidateId
  ?? candidateMutations.rejectCandidate.variables.value?.candidateId
  ?? null)

function translateUnknownError(error: unknown): string | null {
  if (!error) {
    return null
  }
  if (error instanceof LocalApiClientError) {
    return translateErrorCode(error.code, error.message)
  }
  if (error instanceof Error) {
    return error.message
  }
  return String(error)
}

function statusTone(status: KnowledgeCandidateStatus): 'warning' | 'success' | 'error' {
  if (status === 'approved') {
    return 'success'
  }
  if (status === 'rejected') {
    return 'error'
  }
  return 'warning'
}

function statusLabel(status: KnowledgeCandidateStatus): string {
  return t(`apps.knowledge.status.${status}`)
}

function sourceLabel(kind: KnowledgeSourceKind): string {
  return t(`apps.knowledge.sources.${kind}`)
}

function typeLabel(type: KnowledgeCardType): string {
  return t(`apps.knowledge.cardTypes.${type}`)
}

async function handleBackToKnowledge() {
  if (!appId.value) {
    return
  }
  await router.push({ name: 'apps-knowledge', params: { appId: appId.value } })
}

async function handleOpenApp() {
  if (!appId.value) {
    return
  }
  await router.push({ name: 'apps-edit', params: { appId: appId.value } })
}

async function handleApprove(candidate: KnowledgeCandidateRecord) {
  if (!appId.value) {
    return
  }
  const confirmed = window.confirm(t('apps.knowledge.messages.approveConfirm', { title: candidate.candidate.title }))
  if (!confirmed) {
    return
  }
  actionError.value = null
  actionMessage.value = null
  try {
    const result = await candidateMutations.approveCandidate.mutateAsync({
      appId: appId.value,
      candidateId: candidate.candidate_id,
      request: { reviewed_by: 'web-ui', review_note: null },
    })
    actionMessage.value = t('apps.knowledge.messages.approveSuccess', {
      title: result.candidate.candidate.title,
      cardId: result.resolved_card_id,
    })
  } catch (error) {
    actionError.value = translateUnknownError(error) ?? t('apps.knowledge.messages.actionFailed')
  }
}

async function handleReject(candidate: KnowledgeCandidateRecord) {
  if (!appId.value) {
    return
  }
  const confirmed = window.confirm(t('apps.knowledge.messages.rejectConfirm', { title: candidate.candidate.title }))
  if (!confirmed) {
    return
  }
  actionError.value = null
  actionMessage.value = null
  try {
    const result = await candidateMutations.rejectCandidate.mutateAsync({
      appId: appId.value,
      candidateId: candidate.candidate_id,
      request: { reviewed_by: 'web-ui', review_note: null },
    })
    actionMessage.value = t('apps.knowledge.messages.rejectSuccess', {
      title: result.candidate.candidate.title,
    })
  } catch (error) {
    actionError.value = translateUnknownError(error) ?? t('apps.knowledge.messages.actionFailed')
  }
}
</script>

<template>
  <section class="app-page grid gap-4">
    <p v-if="appDetailQuery.isFetching.value && !detail" class="text-sm text-text-secondary">{{ t('common.loading') }}</p>

    <AppEmptyState
      v-else-if="pageErrorMessage"
      :title="t('apps.knowledge.errorTitle')"
      :description="pageErrorMessage"
    />

    <template v-else-if="detail">
      <AppCard class="grid gap-4">
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div class="grid gap-1">
            <div class="flex flex-wrap items-center gap-2">
              <h2 class="text-lg font-semibold text-text-primary">{{ t('apps.knowledge.candidatesPageTitle') }}</h2>
              <AppBadge tone="warning">{{ t('apps.knowledge.summary.pending', { count: pendingCandidates.length }) }}</AppBadge>
            </div>
            <p class="text-sm text-text-secondary">{{ displayAppName }} / {{ detail.profile.app_id }}</p>
            <p class="text-sm text-text-secondary">{{ t('apps.knowledge.candidatesDescription') }}</p>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <UiButton type="button" variant="secondary" @click="() => void candidatesQuery.refetch()">
              <RefreshCcw class="h-4 w-4" />
              {{ t('common.refresh') }}
            </UiButton>
            <UiButton type="button" variant="secondary" @click="handleOpenApp">
              <SquarePen class="h-4 w-4" />
              {{ t('apps.knowledge.actions.openApp') }}
            </UiButton>
            <UiButton type="button" variant="ghost" @click="handleBackToKnowledge">
              <ArrowLeft class="h-4 w-4" />
              {{ t('apps.knowledge.actions.backToKnowledge') }}
            </UiButton>
          </div>
        </div>
      </AppCard>

      <section class="grid gap-4">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div class="grid gap-1">
            <h3 class="text-base font-semibold text-text-primary">{{ t('apps.knowledge.candidatesTitle') }}</h3>
            <p class="text-sm text-text-secondary">{{ t('apps.knowledge.candidatesDescription') }}</p>
          </div>
          <div class="flex flex-wrap gap-2">
            <AppBadge tone="warning">{{ t('apps.knowledge.summary.pending', { count: pendingCandidates.length }) }}</AppBadge>
            <AppBadge tone="success">{{ t('apps.knowledge.summary.approved', { count: approvedCandidates.length }) }}</AppBadge>
            <AppBadge tone="error">{{ t('apps.knowledge.summary.rejected', { count: rejectedCandidates.length }) }}</AppBadge>
          </div>
        </div>

        <AppEmptyState
          v-if="candidatesErrorMessage"
          :title="t('apps.knowledge.errorTitle')"
          :description="candidatesErrorMessage"
        />

        <AppEmptyState
          v-else-if="!candidatesQuery.isFetching.value && candidates.length === 0"
          :title="t('apps.knowledge.candidatesEmptyTitle')"
          :description="t('apps.knowledge.candidatesEmptyDescription')"
        />

        <div v-else class="grid gap-4">
          <p v-if="actionError" class="text-sm text-error-text">{{ actionError }}</p>
          <div
            v-else-if="actionMessage"
            class="rounded-2xl border border-accent/20 bg-accent/5 px-4 py-3 text-sm text-text-secondary"
          >
            {{ actionMessage }}
          </div>

          <div class="grid gap-3">
            <article
              v-for="item in candidates"
              :key="item.candidate_id"
              class="grid gap-3 rounded-xl border border-border-muted bg-surface-muted p-4"
            >
              <div class="flex flex-wrap items-start justify-between gap-3">
                <div class="grid gap-2">
                  <div class="flex flex-wrap items-center gap-2">
                    <h4 class="text-base font-semibold text-text-primary">{{ item.candidate.title }}</h4>
                    <AppBadge :tone="statusTone(item.status)">{{ statusLabel(item.status) }}</AppBadge>
                    <AppBadge tone="neutral">{{ typeLabel(item.candidate.card_type) }}</AppBadge>
                  </div>
                  <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-text-secondary">
                    <span>{{ sourceLabel(item.candidate.source.kind) }}</span>
                    <span>{{ t('apps.knowledge.summary.confidence', { value: item.candidate.confidence.toFixed(2) }) }}</span>
                    <time :datetime="time.datetime(item.submitted_at) ?? undefined" :title="time.tooltip(item.submitted_at)">
                      {{ t('apps.knowledge.summary.submittedAt', { value: time.relative(item.submitted_at) }) }}
                    </time>
                  </div>
                </div>

                <div v-if="item.status === 'pending_review'" class="flex flex-wrap items-center gap-2">
                  <UiButton
                    size="sm"
                    variant="primary"
                    :disabled="candidateMutations.approveCandidate.isPending.value || candidateMutations.rejectCandidate.isPending.value"
                    @click="handleApprove(item)"
                  >
                    <Check class="h-4 w-4" />
                    {{ busyCandidateId === item.candidate_id && candidateMutations.approveCandidate.isPending.value
                      ? t('apps.knowledge.actions.approving')
                      : t('apps.knowledge.actions.approve') }}
                  </UiButton>
                  <UiButton
                    size="sm"
                    variant="danger"
                    :disabled="candidateMutations.approveCandidate.isPending.value || candidateMutations.rejectCandidate.isPending.value"
                    @click="handleReject(item)"
                  >
                    <X class="h-4 w-4" />
                    {{ busyCandidateId === item.candidate_id && candidateMutations.rejectCandidate.isPending.value
                      ? t('apps.knowledge.actions.rejecting')
                      : t('apps.knowledge.actions.reject') }}
                  </UiButton>
                </div>
              </div>

              <p v-if="summarizeKnowledgeCandidate(item.candidate)" class="text-sm text-text-primary">{{ summarizeKnowledgeCandidate(item.candidate) }}</p>

              <dl class="grid gap-2 text-sm text-text-secondary md:grid-cols-3">
                <div class="grid gap-1">
                  <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('apps.knowledge.fields.candidateId') }}</dt>
                  <dd class="break-all">{{ item.candidate_id }}</dd>
                </div>
                <div class="grid gap-1">
                  <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('apps.knowledge.fields.cardId') }}</dt>
                  <dd class="break-all">{{ item.candidate.card_id || item.resolved_card_id || '-' }}</dd>
                </div>
                <div class="grid gap-1">
                  <dt class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('apps.knowledge.fields.evidenceCount') }}</dt>
                  <dd>{{ item.evidence_refs?.length ?? 0 }}</dd>
                </div>
              </dl>

              <div v-if="item.reviewed_by || item.review_note" class="grid gap-1 text-sm text-text-secondary">
                <p v-if="item.reviewed_by">
                  {{ t('apps.knowledge.summary.reviewedBy', { value: item.reviewed_by }) }}
                </p>
                <p v-if="item.review_note">{{ item.review_note }}</p>
              </div>
            </article>
          </div>
        </div>
      </section>
    </template>
  </section>
</template>
