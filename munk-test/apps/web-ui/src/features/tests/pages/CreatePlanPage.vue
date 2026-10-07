<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ArrowLeft, PlusCircle } from '@lucide/vue'

import AppCard from '@/shared/components/AppCard.vue'
import AppEmptyState from '@/shared/components/AppEmptyState.vue'
import UiButton from '@/shared/ui/UiButton.vue'
import UiField from '@/shared/ui/UiField.vue'
import UiInput from '@/shared/ui/UiInput.vue'
import UiSelect from '@/shared/ui/UiSelect.vue'
import UiTextarea from '@/shared/ui/UiTextarea.vue'
import { LocalApiClientError } from '@/shared/api/client'
import { translateErrorCode } from '@/shared/i18n/errorMessages'
import { useAppsQuery } from '@/features/apps/queries/useAppsQuery'
import { useTestPlanCreationMutation } from '@/features/tests/queries/useTestPlanCreationMutation'

const router = useRouter()
const { t } = useI18n()

const appId = ref('')
const requirementDocPath = ref('')
const technicalDocPath = ref('')
const userPrompt = ref('')
const formError = ref<string | null>(null)

const appsQuery = useAppsQuery({})
const createMutation = useTestPlanCreationMutation()
const apps = computed(() => appsQuery.data.value ?? [])
const appOptions = computed(() => apps.value.map((item) => ({
  value: item.app_id,
  label: `${item.app_id} (${item.platform}${item.entry_identity ? ` / ${item.entry_identity}` : ''})`,
})))
const appsErrorMessage = computed(() => {
  const error = appsQuery.error.value
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
})

const submitDisabled = computed(() => (
  appsQuery.isFetching.value
  || createMutation.isPending.value
  || apps.value.length === 0
  || !appId.value.trim()
  || !requirementDocPath.value.trim()
))

async function handleSubmit() {
  formError.value = null
  try {
    const submission = await createMutation.mutateAsync({
      app_id: appId.value.trim(),
      requirement_doc_path: requirementDocPath.value.trim(),
      technical_doc_path: technicalDocPath.value.trim() || null,
      user_prompt: userPrompt.value.trim() || null,
      auto_run: false,
    })
    await router.push(`/tests/create/operations/${encodeURIComponent(submission.operation_id)}`)
  } catch (error) {
    if (error instanceof LocalApiClientError) {
      formError.value = translateErrorCode(error.code, error.message)
    } else if (error instanceof Error) {
      formError.value = error.message
    } else {
      formError.value = String(error)
    }
  }
}

async function handleCancel() {
  await router.push('/tests')
}
</script>

<template>
  <section class="app-page">
    <AppCard class="grid gap-5">
      <UiField :label="t('testsCreate.fields.appId')">
        <UiSelect v-model="appId" :options="appOptions" :placeholder="t('testsCreate.placeholders.appId')" :disabled="appsQuery.isFetching.value || apps.length === 0" />
      </UiField>

      <UiField :label="t('testsCreate.fields.requirementDocPath')">
        <UiInput v-model="requirementDocPath" :placeholder="t('testsCreate.placeholders.requirementDocPath')" />
      </UiField>

      <UiField :label="t('testsCreate.fields.technicalDocPath')">
        <UiInput v-model="technicalDocPath" :placeholder="t('testsCreate.placeholders.technicalDocPath')" />
      </UiField>

      <UiField :label="t('testsCreate.fields.userPrompt')">
        <UiTextarea v-model="userPrompt" :placeholder="t('testsCreate.placeholders.userPrompt')" :rows="8" />
      </UiField>

      <AppEmptyState
        v-if="appsErrorMessage"
        :title="t('testsCreate.errorTitle')"
        :description="appsErrorMessage"
      />

      <AppEmptyState
        v-else-if="!appsQuery.isFetching.value && apps.length === 0"
        :title="t('testsCreate.emptyAppsTitle')"
        :description="t('testsCreate.emptyAppsDescription')"
      />

      <AppEmptyState
        v-if="formError"
        :title="t('testsCreate.errorTitle')"
        :description="formError"
      />

      <div class="flex flex-wrap justify-end gap-3">
        <UiButton type="button" variant="secondary" @click="handleCancel">
          <ArrowLeft class="h-4 w-4" />
          {{ t('testsCreate.actions.cancel') }}
        </UiButton>
        <UiButton type="button" variant="primary" :disabled="submitDisabled" @click="handleSubmit">
          <PlusCircle class="h-4 w-4" />
          {{ createMutation.isPending.value ? t('testsCreate.actions.submitting') : t('testsCreate.actions.create') }}
        </UiButton>
      </div>
    </AppCard>
  </section>
</template>
