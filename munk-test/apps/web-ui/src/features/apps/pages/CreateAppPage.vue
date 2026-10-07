<script setup lang="ts">
import { ArrowLeft, PlusCircle } from '@lucide/vue'
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import AppCard from '@/shared/components/AppCard.vue'
import AppEmptyState from '@/shared/components/AppEmptyState.vue'
import { LocalApiClientError } from '@/shared/api/client'
import { translateErrorCode } from '@/shared/i18n/errorMessages'
import UiButton from '@/shared/ui/UiButton.vue'
import { useAppMutations } from '@/features/apps/queries/useAppMutations'
import AppFormFields from '../components/AppFormFields.vue'
import { buildAppUpsertRequest, createAppFormModel, isAppFormSubmittable } from '../form'

const router = useRouter()
const { t } = useI18n()
const mutations = useAppMutations()
const submitError = ref<string | null>(null)

const form = reactive(createAppFormModel())

const isBusy = computed(() => mutations.createApp.isPending.value)
const saveDisabled = computed(() => isBusy.value || !isAppFormSubmittable(form))

async function handleSubmit() {
  submitError.value = null
  try {
    await mutations.createApp.mutateAsync(buildAppUpsertRequest(form))
    await router.push({ name: 'apps' })
  } catch (error) {
    if (error instanceof LocalApiClientError) {
      submitError.value = translateErrorCode(error.code, error.message)
    } else if (error instanceof Error) {
      submitError.value = error.message
    } else {
      submitError.value = String(error)
    }
  }
}

async function handleCancel() {
  await router.push({ name: 'apps' })
}
</script>

<template>
  <section class="app-page">
    <AppCard class="grid gap-5">
      <div>
        <h2 class="text-base font-semibold text-text-primary">{{ t('apps.editor.createTitle') }}</h2>
        <p class="text-sm text-text-secondary">{{ t('apps.editor.description') }}</p>
      </div>

      <AppFormFields :form="form" />

      <AppEmptyState
        v-if="submitError"
        :title="t('apps.errorTitle')"
        :description="submitError"
      />

      <div class="flex flex-wrap justify-end gap-3">
        <UiButton type="button" variant="secondary" @click="handleCancel">
          <ArrowLeft class="h-4 w-4" />
          {{ t('apps.actions.cancelCreate') }}
        </UiButton>
        <UiButton type="button" variant="primary" :disabled="saveDisabled" @click="handleSubmit">
          <PlusCircle class="h-4 w-4" />
          {{ isBusy ? t('apps.actions.saving') : t('apps.actions.createApp') }}
        </UiButton>
      </div>
    </AppCard>
  </section>
</template>
