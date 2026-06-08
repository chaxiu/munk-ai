<script setup lang="ts">
import { ArrowLeft, BookOpen, Save, Trash2 } from '@lucide/vue'
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import AppCard from '@/shared/components/AppCard.vue'
import AppEmptyState from '@/shared/components/AppEmptyState.vue'
import { LocalApiClientError } from '@/shared/api/client'
import { translateErrorCode } from '@/shared/i18n/errorMessages'
import UiButton from '@/shared/ui/UiButton.vue'
import { useAppDetailQuery } from '@/features/apps/queries/useAppDetailQuery'
import { useAppMutations } from '@/features/apps/queries/useAppMutations'
import AppFormFields from '../components/AppFormFields.vue'
import { buildAppUpsertRequest, createAppFormModel, isAppFormSubmittable, populateAppForm } from '../form'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const mutations = useAppMutations()
const submitError = ref<string | null>(null)

const appId = computed(() => {
  const value = route.params.appId
  return typeof value === 'string' ? value : null
})

const form = reactive(createAppFormModel())

const appDetailQuery = useAppDetailQuery(appId)
const detail = computed(() => appDetailQuery.data.value)
const isBusy = computed(() => (
  mutations.updateApp.isPending.value
  || mutations.deleteApp.isPending.value
))
const detailErrorMessage = computed(() => translateUnknownError(appDetailQuery.error.value))
const saveDisabled = computed(() => isBusy.value || !isAppFormSubmittable(form))

watch(detail, (value) => {
  if (!value) {
    return
  }
  populateAppForm(form, value)
}, { immediate: true })

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

async function handleBack() {
  await router.push({ name: 'apps' })
}

async function handleOpenKnowledge() {
  if (!appId.value) {
    return
  }
  await router.push({ name: 'apps-knowledge', params: { appId: appId.value } })
}

async function handleSave() {
  submitError.value = null
  try {
    if (!appId.value) {
      return
    }
    await mutations.updateApp.mutateAsync({
      appId: appId.value,
      request: buildAppUpsertRequest(form),
    })
  } catch (error) {
    submitError.value = translateUnknownError(error) ?? t('apps.errorTitle')
  }
}

async function handleDelete() {
  if (!appId.value) {
    return
  }
  const confirmed = window.confirm(t('apps.messages.deleteConfirm', { appId: appId.value }))
  if (!confirmed) {
    return
  }
  submitError.value = null
  try {
    await mutations.deleteApp.mutateAsync(appId.value)
    await router.push({ name: 'apps' })
  } catch (error) {
    submitError.value = translateUnknownError(error) ?? t('apps.errorTitle')
  }
}
</script>

<template>
  <section class="app-page">
    <AppCard class="grid gap-5">
      <div>
        <h2 class="text-base font-semibold text-text-primary">{{ t('apps.editor.editTitle') }}</h2>
        <p class="text-sm text-text-secondary">{{ t('apps.editor.description') }}</p>
      </div>

      <AppEmptyState
        v-if="detailErrorMessage"
        :title="t('apps.errorTitle')"
        :description="detailErrorMessage"
      />

      <AppCard v-else-if="appDetailQuery.isFetching.value" class="border-dashed">
        <p class="muted">{{ t('common.loading') }}</p>
      </AppCard>

      <template v-else>
        <AppFormFields :form="form" :app-id-readonly="true" />

        <AppEmptyState
          v-if="submitError"
          :title="t('apps.errorTitle')"
          :description="submitError"
        />

        <div class="flex flex-wrap justify-end gap-3">
          <UiButton type="button" variant="danger" :disabled="isBusy" @click="handleDelete">
            <Trash2 class="h-4 w-4" />
            {{ t('apps.actions.deleteApp') }}
          </UiButton>
          <UiButton type="button" variant="secondary" :disabled="isBusy" @click="handleOpenKnowledge">
            <BookOpen class="h-4 w-4" />
            {{ t('apps.actions.openKnowledge') }}
          </UiButton>
          <UiButton type="button" variant="secondary" :disabled="isBusy" @click="handleBack">
            <ArrowLeft class="h-4 w-4" />
            {{ t('apps.actions.closeEditor') }}
          </UiButton>
          <UiButton type="button" variant="primary" :disabled="saveDisabled" @click="handleSave">
            <Save class="h-4 w-4" />
            {{ isBusy ? t('apps.actions.saving') : t('apps.actions.saveApp') }}
          </UiButton>
        </div>
      </template>
    </AppCard>
  </section>
</template>
