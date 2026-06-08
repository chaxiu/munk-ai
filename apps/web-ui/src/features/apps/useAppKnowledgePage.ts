import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import {
  createEmptyKnowledgeCardForm,
  formFromKnowledgeCard,
  toKnowledgeCardInput,
  updateFormCardType,
} from '@/features/apps/knowledgeEditor'
import { parseKnowledgeDocument } from '@/features/apps/knowledgePresentation'
import { useAppDetailQuery } from '@/features/apps/queries/useAppDetailQuery'
import { useAppKnowledgeCandidatesQuery } from '@/features/apps/queries/useAppKnowledgeCandidatesQuery'
import { useAppKnowledgeCardsQuery } from '@/features/apps/queries/useAppKnowledgeCardsQuery'
import { useKnowledgeCardDetailQuery } from '@/features/apps/queries/useKnowledgeCardDetailQuery'
import { useKnowledgeCardMutations } from '@/features/apps/queries/useKnowledgeCardMutations'
import { LocalApiClientError } from '@/shared/api/client'
import type { KnowledgeCardStatus, KnowledgeCardType, KnowledgeSourceKind } from '@/shared/api/knowledge'
import { translateErrorCode } from '@/shared/i18n/errorMessages'

export function useAppKnowledgePage() {
  const route = useRoute()
  const router = useRouter()
  const { t } = useI18n()
  const cardMutations = useKnowledgeCardMutations()

  const queryFilter = ref('')
  const cardTypeFilter = ref<KnowledgeCardType | ''>('')
  const statusFilter = ref<KnowledgeCardStatus | ''>('')
  const isCreating = ref(false)
  const form = ref(createEmptyKnowledgeCardForm())
  const actionError = ref<string | null>(null)
  const actionMessage = ref<string | null>(null)
  const payloadError = ref<string | null>(null)

  const appId = computed(() => {
    const value = route.params.appId
    return typeof value === 'string' ? value : null
  })
  const selectedCardId = computed(() => {
    const value = route.query.cardId
    return typeof value === 'string' ? value : null
  })

  const appDetailQuery = useAppDetailQuery(appId)
  const cardsQuery = useAppKnowledgeCardsQuery(computed(() => ({
    appId: appId.value,
    query: queryFilter.value.trim() || undefined,
    cardType: cardTypeFilter.value || undefined,
    status: statusFilter.value || undefined,
    limit: 200,
    offset: 0,
  })))
  const selectedCardQuery = useKnowledgeCardDetailQuery(computed(() => ({
    appId: appId.value,
    cardId: selectedCardId.value,
  })))
  const candidatesQuery = useAppKnowledgeCandidatesQuery(computed(() => ({
    appId: appId.value,
  })))

  const detail = computed(() => appDetailQuery.data.value)
  const cards = computed(() => cardsQuery.data.value?.items ?? [])
  const selectedCard = computed(() => (
    selectedCardQuery.data.value?.card
    ?? cards.value.find(item => item.card_id === selectedCardId.value)
    ?? null
  ))
  const candidates = computed(() => candidatesQuery.data.value?.items ?? [])
  const pendingCandidateCount = computed(() => candidates.value.filter(item => item.status === 'pending_review').length)
  const knowledgeSummary = computed(() => parseKnowledgeDocument(detail.value?.app_knowledge_content))
  const displayAppName = computed(() => {
    const profile = detail.value?.profile
    if (!profile) {
      return appId.value ?? '-'
    }
    return profile.app_name?.trim() || profile.app_id
  })
  const pageErrorMessage = computed(() => translateUnknownError(appDetailQuery.error.value))
  const cardsErrorMessage = computed(() => translateUnknownError(cardsQuery.error.value))
  const selectedCardErrorMessage = computed(() => translateUnknownError(selectedCardQuery.error.value))
  const isSaving = computed(() => cardMutations.createCard.isPending.value || cardMutations.updateCard.isPending.value)
  const isDeleting = computed(() => cardMutations.deleteCard.isPending.value)

  const cardTypeOptions = computed(() => [
    { value: 'screen', label: typeLabel(t, 'screen') },
    { value: 'flow', label: typeLabel(t, 'flow') },
    { value: 'assertion', label: typeLabel(t, 'assertion') },
    { value: 'issue', label: typeLabel(t, 'issue') },
    { value: 'data', label: typeLabel(t, 'data') },
    { value: 'policy', label: typeLabel(t, 'policy') },
    { value: 'domain_term', label: typeLabel(t, 'domain_term') },
  ])

  const sourceKindOptions = computed(() => [
    { value: 'manual', label: sourceLabel(t, 'manual') },
    { value: 'import', label: sourceLabel(t, 'import') },
    { value: 'review', label: sourceLabel(t, 'review') },
    { value: 'knowledge_agent', label: sourceLabel(t, 'knowledge_agent') },
  ])

  const statusOptions = computed(() => [
    { value: 'active', label: cardStatusLabel(t, 'active') },
    { value: 'deprecated', label: cardStatusLabel(t, 'deprecated') },
    { value: 'archived', label: cardStatusLabel(t, 'archived') },
  ])

  const cardTypeFilterOptions = computed(() => [
    { value: '', label: t('apps.knowledge.filters.allTypes') },
    ...cardTypeOptions.value,
  ])

  const statusFilterOptions = computed(() => [
    { value: '', label: t('apps.knowledge.filters.allStatuses') },
    ...statusOptions.value,
  ])

  watch(cards, (nextCards) => {
    if (isCreating.value) {
      return
    }
    if (nextCards.length === 0) {
      if (selectedCardId.value) {
        void syncSelectedCard(router, appId.value, selectedCardId.value, null)
      }
      return
    }
    if (!selectedCardId.value) {
      void syncSelectedCard(router, appId.value, null, nextCards[0]?.card_id ?? null)
      return
    }
    if (!nextCards.some(item => item.card_id === selectedCardId.value)) {
      void syncSelectedCard(router, appId.value, selectedCardId.value, nextCards[0]?.card_id ?? null)
    }
  }, { immediate: true })

  watch(selectedCard, (card) => {
    if (!card || isCreating.value) {
      return
    }
    form.value = formFromKnowledgeCard(card)
    payloadError.value = null
  }, { immediate: true })

  async function handleBackToApps() {
    await router.push({ name: 'apps' })
  }

  async function handleOpenApp() {
    if (!appId.value) {
      return
    }
    await router.push({ name: 'apps-edit', params: { appId: appId.value } })
  }

  async function handleOpenCandidates() {
    if (!appId.value) {
      return
    }
    await router.push({ name: 'apps-knowledge-candidates', params: { appId: appId.value } })
  }

  async function handleRefresh() {
    await Promise.all([
      appDetailQuery.refetch(),
      cardsQuery.refetch(),
      candidatesQuery.refetch(),
      selectedCardId.value ? selectedCardQuery.refetch() : Promise.resolve(),
    ])
  }

  function handleStartCreate() {
    isCreating.value = true
    actionError.value = null
    actionMessage.value = null
    payloadError.value = null
    form.value = createEmptyKnowledgeCardForm()
    void syncSelectedCard(router, appId.value, selectedCardId.value, null)
  }

  function handleSelectCard(cardId: string) {
    isCreating.value = false
    actionError.value = null
    actionMessage.value = null
    payloadError.value = null
    void syncSelectedCard(router, appId.value, selectedCardId.value, cardId)
  }

  function handleResetEditor() {
    actionError.value = null
    actionMessage.value = null
    payloadError.value = null
    if (isCreating.value) {
      form.value = createEmptyKnowledgeCardForm(form.value.cardType)
      return
    }
    if (selectedCard.value) {
      form.value = formFromKnowledgeCard(selectedCard.value)
    }
  }

  function handleCardTypeChange(value: KnowledgeCardType) {
    form.value = updateFormCardType(form.value, value)
    payloadError.value = null
  }

  async function handleSaveCard() {
    if (!appId.value) {
      return
    }
    actionError.value = null
    actionMessage.value = null
    payloadError.value = null
    try {
      const card = toKnowledgeCardInput({
        appId: appId.value,
        form: form.value,
        includeCardId: !isCreating.value,
      })
      if (isCreating.value) {
        const result = await cardMutations.createCard.mutateAsync({ appId: appId.value, card })
        form.value = formFromKnowledgeCard(result.card)
        isCreating.value = false
        actionMessage.value = t('apps.knowledge.messages.createSuccess', { title: result.card.title })
        await syncSelectedCard(router, appId.value, selectedCardId.value, result.card.card_id)
        return
      }
      if (!selectedCardId.value) {
        return
      }
      const result = await cardMutations.updateCard.mutateAsync({
        appId: appId.value,
        cardId: selectedCardId.value,
        card,
      })
      form.value = formFromKnowledgeCard(result.card)
      actionMessage.value = t('apps.knowledge.messages.updateSuccess', { title: result.card.title })
    } catch (error) {
      const message = translateUnknownError(error) ?? t('apps.knowledge.messages.actionFailed')
      if (message.includes('payload')) {
        payloadError.value = t('apps.knowledge.messages.payloadInvalid')
      } else {
        actionError.value = message
      }
    }
  }

  async function handleDeleteCard() {
    if (!appId.value || !selectedCard.value || isCreating.value) {
      return
    }
    const confirmed = window.confirm(t('apps.knowledge.messages.deleteConfirm', { title: selectedCard.value.title }))
    if (!confirmed) {
      return
    }
    actionError.value = null
    actionMessage.value = null
    payloadError.value = null
    try {
      await cardMutations.deleteCard.mutateAsync({
        appId: appId.value,
        cardId: selectedCard.value.card_id,
      })
      actionMessage.value = t('apps.knowledge.messages.deleteSuccess', { title: selectedCard.value.title })
      await syncSelectedCard(router, appId.value, selectedCardId.value, null)
    } catch (error) {
      actionError.value = translateUnknownError(error) ?? t('apps.knowledge.messages.actionFailed')
    }
  }

  return {
    appId,
    detail,
    cards,
    selectedCard,
    knowledgeSummary,
    displayAppName,
    pendingCandidateCount,
    pageErrorMessage,
    cardsErrorMessage,
    selectedCardErrorMessage,
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
  }
}

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

async function syncSelectedCard(
  router: ReturnType<typeof useRouter>,
  appId: string | null,
  currentCardId: string | null,
  nextCardId: string | null,
) {
  if (!appId) {
    return
  }
  if ((currentCardId ?? null) === (nextCardId ?? null)) {
    return
  }
  await router.replace({
    name: 'apps-knowledge',
    params: { appId },
    query: nextCardId ? { cardId: nextCardId } : {},
  })
}

function typeLabel(t: ReturnType<typeof useI18n>['t'], type: KnowledgeCardType): string {
  return t(`apps.knowledge.cardTypes.${type}`)
}

function sourceLabel(t: ReturnType<typeof useI18n>['t'], kind: KnowledgeSourceKind): string {
  return t(`apps.knowledge.sources.${kind}`)
}

function cardStatusLabel(t: ReturnType<typeof useI18n>['t'], status: KnowledgeCardStatus): string {
  return t(`apps.knowledge.cardStatus.${status}`)
}
