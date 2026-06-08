<script setup lang="ts">
import AppKnowledgeHeader from '@/features/apps/components/AppKnowledgeHeader.vue'
import KnowledgeCardEditor from '@/features/apps/components/KnowledgeCardEditor.vue'
import KnowledgeCardsSidebar from '@/features/apps/components/KnowledgeCardsSidebar.vue'
import { useAppKnowledgePage } from '@/features/apps/useAppKnowledgePage'
import AppEmptyState from '@/shared/components/AppEmptyState.vue'

const {
  detail,
  displayAppName,
  pendingCandidateCount,
  pageErrorMessage,
  cardsErrorMessage,
  selectedCardErrorMessage,
  cards,
  selectedCard,
  queryFilter,
  cardTypeFilter,
  statusFilter,
  isCreating,
  form,
  actionError,
  actionMessage,
  payloadError,
  isSaving,
  isDeleting,
  selectedCardId,
  appDetailQuery,
  cardsQuery,
  cardTypeFilterOptions,
  statusFilterOptions,
  cardTypeOptions,
  sourceKindOptions,
  statusOptions,
  handleBackToApps,
  handleOpenApp,
  handleOpenCandidates,
  handleRefresh,
  handleStartCreate,
  handleSelectCard,
  handleResetEditor,
  handleCardTypeChange,
  handleSaveCard,
  handleDeleteCard,
} = useAppKnowledgePage()
</script>

<template>
  <section class="app-page box-border flex h-[calc(100vh-3.5rem)] min-h-[calc(100vh-3.5rem)] flex-col gap-3 overflow-hidden">
    <p v-if="appDetailQuery.isFetching.value && !detail" class="text-sm text-text-secondary">{{ $t('common.loading') }}</p>

    <AppEmptyState
      v-else-if="pageErrorMessage"
      :title="$t('apps.knowledge.errorTitle')"
      :description="pageErrorMessage"
    />

    <template v-else-if="detail">
      <AppKnowledgeHeader
        :platform="detail.profile.platform"
        :display-app-name="displayAppName"
        :app-id="detail.profile.app_id"
        :pending-candidate-label="$t('apps.knowledge.summary.pending', { count: pendingCandidateCount })"
        @refresh="handleRefresh"
        @open-app="handleOpenApp"
        @open-candidates="handleOpenCandidates"
        @back="handleBackToApps"
      />

      <section class="grid min-h-0 flex-1 gap-3 xl:grid-cols-[minmax(280px,22rem)_minmax(0,1fr)] xl:items-stretch">
        <KnowledgeCardsSidebar
          :cards="cards"
          :cards-error-message="cardsErrorMessage"
          :is-fetching="cardsQuery.isFetching.value"
          :selected-card-id="selectedCardId"
          :is-creating="isCreating"
          :query-filter="queryFilter"
          :card-type-filter="cardTypeFilter"
          :status-filter="statusFilter"
          :card-type-filter-options="cardTypeFilterOptions"
          :status-filter-options="statusFilterOptions"
          @new-card="handleStartCreate"
          @select-card="handleSelectCard"
          @update:query-filter="queryFilter = $event"
          @update:card-type-filter="cardTypeFilter = $event"
          @update:status-filter="statusFilter = $event"
        />

        <KnowledgeCardEditor
          v-model:form="form"
          :selected-card="selectedCard"
          :selected-card-error-message="selectedCardErrorMessage"
          :is-creating="isCreating"
          :is-fetching="cardsQuery.isFetching.value"
          :is-saving="isSaving"
          :is-deleting="isDeleting"
          :action-error="actionError"
          :action-message="actionMessage"
          :payload-error="payloadError"
          :card-type-options="cardTypeOptions"
          :source-kind-options="sourceKindOptions"
          :status-options="statusOptions"
          @save="handleSaveCard"
          @reset="handleResetEditor"
          @delete="handleDeleteCard"
          @new-card="handleStartCreate"
          @card-type-change="handleCardTypeChange"
        />
      </section>
    </template>
  </section>
</template>
