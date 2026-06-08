<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import AppEmptyState from '@/shared/components/AppEmptyState.vue'
import UiButton from '@/shared/ui/UiButton.vue'
import UiField from '@/shared/ui/UiField.vue'
import UiInput from '@/shared/ui/UiInput.vue'
import UiSelect from '@/shared/ui/UiSelect.vue'
import { LocalApiClientError } from '@/shared/api/client'
import { translateErrorCode } from '@/shared/i18n/errorMessages'
import { useAppsQuery } from '@/features/apps/queries/useAppsQuery'
import { usePlanImportMutation } from '@/features/tests/queries/usePlanImportMutation'

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  close: []
}>()

const { t } = useI18n()
const router = useRouter()

const appsQuery = useAppsQuery({})
const importMutation = usePlanImportMutation()

const planName = ref('')
const appId = ref('')
const formError = ref<string | null>(null)
const selectedFileName = ref('')
const rawPlan = ref<Record<string, unknown> | null>(null)

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
  || importMutation.isPending.value
  || apps.value.length === 0
  || !planName.value.trim()
  || !appId.value.trim()
  || rawPlan.value == null
))

watch(() => props.open, (open) => {
  if (open) {
    formError.value = null
    if (!appId.value && apps.value.length > 0) {
      appId.value = apps.value[0]!.app_id
    }
    return
  }
  resetForm()
})

async function handleFileChange(event: Event) {
  formError.value = null
  const input = event.target as HTMLInputElement | null
  const file = input?.files?.[0]
  if (!file) {
    selectedFileName.value = ''
    rawPlan.value = null
    return
  }
  selectedFileName.value = file.name
  try {
    const text = await file.text()
    const parsed = JSON.parse(text) as unknown
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error(t('tests.import.errors.invalidJson'))
    }
    const cases = (parsed as { cases?: unknown }).cases
    if (!Array.isArray(cases)) {
      throw new Error(t('tests.import.errors.missingRequiredFields'))
    }
    if (cases.length === 0) {
      throw new Error(t('tests.import.errors.emptyCases'))
    }
    const firstCase = cases[0]
    if (!firstCase || typeof firstCase !== 'object' || Array.isArray(firstCase)) {
      throw new Error(t('tests.import.errors.missingRequiredFields'))
    }
    const draft = firstCase as { title?: unknown, intent?: unknown, runner_goal?: unknown }
    if (
      typeof draft.title !== 'string'
      || typeof draft.intent !== 'string'
      || typeof draft.runner_goal !== 'string'
      || !draft.title.trim()
      || !draft.intent.trim()
      || !draft.runner_goal.trim()
    ) {
      throw new Error(t('tests.import.errors.missingRequiredFields'))
    }
    rawPlan.value = parsed as Record<string, unknown>
  } catch (error) {
    rawPlan.value = null
    if (error instanceof Error) {
      formError.value = error.message
    } else {
      formError.value = String(error)
    }
  }
}

async function handleSubmit() {
  if (submitDisabled.value || rawPlan.value == null) {
    return
  }
  formError.value = null
  try {
    const result = await importMutation.mutateAsync({
      app_id: appId.value.trim(),
      name: planName.value.trim(),
      file_name: selectedFileName.value || null,
      raw_plan: rawPlan.value,
    })
    emit('close')
    await router.push(`/tests/plans/${encodeURIComponent(result.app_id)}/${encodeURIComponent(result.plan_id)}`)
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

function handleClose() {
  emit('close')
}

function resetForm() {
  planName.value = ''
  formError.value = null
  selectedFileName.value = ''
  rawPlan.value = null
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="fixed inset-0 z-[80] flex items-center justify-center px-4">
      <button type="button" class="absolute inset-0 bg-surface-overlay/60 backdrop-blur-sm" @click="handleClose" />
      <div class="relative z-[81] grid w-full max-w-2xl gap-5 rounded-2xl border border-border bg-surface-default p-6 shadow-panel">
        <div class="grid gap-1">
          <h2 class="text-lg font-semibold text-text-primary">{{ t('tests.import.dialog.title') }}</h2>
          <p class="text-sm text-text-secondary">{{ t('tests.import.dialog.description') }}</p>
        </div>

        <UiField :label="t('tests.import.fields.name')">
          <UiInput v-model="planName" :placeholder="t('tests.import.placeholders.name')" />
        </UiField>

        <UiField :label="t('tests.import.fields.appId')">
          <UiSelect v-model="appId" :options="appOptions" :placeholder="t('tests.import.placeholders.appId')" :disabled="appsQuery.isFetching.value || apps.length === 0" />
        </UiField>

        <UiField :label="t('tests.import.fields.file')">
          <div class="grid gap-2">
            <input
              class="block w-full rounded-xl border border-border bg-surface-default px-3 py-2 text-sm text-text-primary file:mr-3 file:rounded-lg file:border-0 file:bg-accent-soft file:px-3 file:py-2 file:text-sm file:font-medium file:text-accent hover:border-border-strong"
              type="file"
              accept=".json,application/json"
              @change="handleFileChange"
            >
            <p v-if="selectedFileName" class="text-xs text-text-secondary">{{ selectedFileName }}</p>
          </div>
        </UiField>

        <AppEmptyState
          v-if="appsErrorMessage"
          :title="t('tests.import.errorTitle')"
          :description="appsErrorMessage"
        />

        <AppEmptyState
          v-else-if="!appsQuery.isFetching.value && apps.length === 0"
          :title="t('tests.import.emptyAppsTitle')"
          :description="t('tests.import.emptyAppsDescription')"
        />

        <AppEmptyState
          v-if="formError"
          :title="t('tests.import.errorTitle')"
          :description="formError"
        />

        <div class="flex flex-wrap justify-end gap-3">
          <UiButton type="button" variant="secondary" @click="handleClose">
            {{ t('tests.import.actions.cancel') }}
          </UiButton>
          <UiButton type="button" variant="primary" :disabled="submitDisabled" @click="handleSubmit">
            {{ importMutation.isPending.value ? t('tests.import.actions.submitting') : t('tests.import.actions.submit') }}
          </UiButton>
        </div>
      </div>
    </div>
  </Teleport>
</template>
