<script setup lang="ts">
import { PlusCircle, Save, Trash2 } from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import type { KnowledgeCardEditorForm } from '@/features/apps/knowledgeEditor'
import type { KnowledgeCard, KnowledgeCardType, KnowledgeSourceKind } from '@/shared/api/knowledge'
import AppEmptyState from '@/shared/components/AppEmptyState.vue'
import { useTime } from '@/shared/time/useTime'
import UiButton from '@/shared/ui/UiButton.vue'
import UiField from '@/shared/ui/UiField.vue'
import UiInput from '@/shared/ui/UiInput.vue'
import UiSelect from '@/shared/ui/UiSelect.vue'
import UiTextarea from '@/shared/ui/UiTextarea.vue'

const props = defineProps<{
  selectedCard: KnowledgeCard | null
  selectedCardErrorMessage: string | null
  isCreating: boolean
  isFetching: boolean
  isSaving: boolean
  isDeleting: boolean
  actionError: string | null
  actionMessage: string | null
  payloadError: string | null
  cardTypeOptions: Array<{ value: string, label: string }>
  sourceKindOptions: Array<{ value: string, label: string }>
  statusOptions: Array<{ value: string, label: string }>
}>()

const form = defineModel<KnowledgeCardEditorForm>('form', { required: true })

const emit = defineEmits<{
  save: []
  reset: []
  delete: []
  newCard: []
  cardTypeChange: [value: KnowledgeCardType]
}>()

const { t } = useI18n()
const time = useTime()
const hasEditorContent = computed(() => props.isCreating || Boolean(props.selectedCard))

function sourceLabel(kind: KnowledgeSourceKind): string {
  return t(`apps.knowledge.sources.${kind}`)
}
</script>

<template>
  <div class="flex h-full min-h-0 flex-col gap-4 rounded-2xl border border-border bg-surface-elevated p-4">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div class="grid gap-1">
        <h3 class="text-base font-semibold text-text-primary">
          {{ props.isCreating ? $t('apps.knowledge.editor.createTitle') : $t('apps.knowledge.editor.editTitle') }}
        </h3>
        <p class="text-sm text-text-secondary">{{ $t('apps.knowledge.editor.description') }}</p>
      </div>
      <div class="flex flex-wrap gap-2">
        <UiButton type="button" variant="secondary" :disabled="props.isSaving || props.isDeleting || !hasEditorContent" @click="$emit('reset')">
          {{ $t('apps.knowledge.actions.resetEditor') }}
        </UiButton>
        <UiButton type="button" variant="primary" :disabled="props.isSaving || props.isDeleting || !hasEditorContent" @click="$emit('save')">
          <Save class="h-4 w-4" />
          {{ props.isSaving ? $t('apps.knowledge.actions.savingCard') : $t('apps.knowledge.actions.saveCard') }}
        </UiButton>
        <UiButton
          v-if="props.selectedCard && !props.isCreating"
          type="button"
          variant="danger"
          :disabled="props.isSaving || props.isDeleting"
          @click="$emit('delete')"
        >
          <Trash2 class="h-4 w-4" />
          {{ props.isDeleting ? $t('apps.knowledge.actions.deletingCard') : $t('apps.knowledge.actions.deleteCard') }}
        </UiButton>
      </div>
    </div>

    <AppEmptyState
      v-if="!props.isCreating && !props.selectedCard && !props.isFetching"
      :title="$t('apps.knowledge.editor.emptyTitle')"
      :description="$t('apps.knowledge.editor.emptyDescription')"
    >
      <template #actions>
        <UiButton type="button" variant="primary" @click="$emit('newCard')">
          <PlusCircle class="h-4 w-4" />
          {{ $t('apps.knowledge.actions.newCard') }}
        </UiButton>
      </template>
    </AppEmptyState>

    <AppEmptyState
      v-else-if="props.selectedCardErrorMessage && !props.isCreating"
      :title="$t('apps.knowledge.errorTitle')"
      :description="props.selectedCardErrorMessage"
    />

    <div v-else class="min-h-0 flex-1 overflow-y-auto pr-1 scrollbar-subtle">
      <div class="grid gap-4">
        <p v-if="props.actionError" class="text-sm text-error-text">{{ props.actionError }}</p>
        <div
          v-else-if="props.actionMessage"
          class="rounded-2xl border border-accent/20 bg-accent/5 px-4 py-3 text-sm text-text-secondary"
        >
          {{ props.actionMessage }}
        </div>

        <div v-if="props.selectedCard && !props.isCreating" class="grid gap-3 md:grid-cols-3">
          <div class="rounded-xl border border-border-muted bg-surface-muted p-4">
            <p class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ $t('apps.knowledge.fields.cardId') }}</p>
            <p class="mt-1 break-all text-sm text-text-primary">{{ props.selectedCard.card_id }}</p>
          </div>
          <div class="rounded-xl border border-border-muted bg-surface-muted p-4">
            <p class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ $t('apps.knowledge.fields.updatedAt') }}</p>
            <p class="mt-1 text-sm text-text-primary">{{ time.tooltip(props.selectedCard.updated_at) || props.selectedCard.updated_at }}</p>
          </div>
          <div class="rounded-xl border border-border-muted bg-surface-muted p-4">
            <p class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ $t('apps.knowledge.fields.sourceKind') }}</p>
            <p class="mt-1 text-sm text-text-primary">{{ sourceLabel(props.selectedCard.source.kind) }}</p>
          </div>
        </div>

        <div class="grid gap-4 md:grid-cols-2">
          <UiField :label="$t('apps.knowledge.fields.title')">
            <UiInput v-model="form.title" :disabled="props.isSaving || props.isDeleting" />
          </UiField>
          <UiField :label="$t('apps.knowledge.fields.cardType')">
            <UiSelect
              :model-value="form.cardType"
              :options="props.cardTypeOptions"
              :disabled="props.isSaving || props.isDeleting"
              @update:model-value="emit('cardTypeChange', $event as KnowledgeCardType)"
            />
          </UiField>
          <UiField :label="$t('apps.knowledge.fields.status')">
            <UiSelect v-model="form.status" :options="props.statusOptions" :disabled="props.isSaving || props.isDeleting" />
          </UiField>
          <UiField :label="$t('apps.knowledge.fields.confidence')" :hint="$t('apps.knowledge.fields.confidenceHint')">
            <UiInput v-model="form.confidence" :disabled="props.isSaving || props.isDeleting" inputmode="decimal" />
          </UiField>
          <UiField :label="$t('apps.knowledge.fields.sourceKind')">
            <UiSelect v-model="form.sourceKind" :options="props.sourceKindOptions" :disabled="props.isSaving || props.isDeleting" />
          </UiField>
          <UiField :label="$t('apps.knowledge.fields.sourceRef')" :hint="$t('apps.fields.optional')">
            <UiInput v-model="form.sourceRef" :disabled="props.isSaving || props.isDeleting" />
          </UiField>
        </div>

        <UiField :label="$t('apps.knowledge.fields.sourceNote')" :hint="$t('apps.fields.optional')">
          <UiTextarea v-model="form.sourceNote" :rows="3" :disabled="props.isSaving || props.isDeleting" />
        </UiField>

        <UiField
          :label="$t('apps.knowledge.fields.payload')"
          :hint="$t('apps.knowledge.fields.payloadHint')"
          :error="props.payloadError"
        >
          <UiTextarea v-model="form.payloadText" :rows="14" :disabled="props.isSaving || props.isDeleting" />
        </UiField>
      </div>
    </div>
  </div>
</template>
