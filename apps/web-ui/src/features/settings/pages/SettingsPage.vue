<script setup lang="ts">
import { Save, RefreshCw } from '@lucide/vue'
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import AgentConfigCard from '@/features/settings/components/AgentConfigCard.vue'
import OrchestrationConfigForm from '@/features/settings/components/OrchestrationConfigForm.vue'
import ProxyConfigForm from '@/features/settings/components/ProxyConfigForm.vue'
import RuntimeConfigForm from '@/features/settings/components/RuntimeConfigForm.vue'
import ProviderSectionForm from '@/features/settings/components/ProviderSectionForm.vue'
import { useSettingsConfigMutation } from '@/features/settings/queries/useSettingsConfigMutation'
import { useSettingsConfigQuery } from '@/features/settings/queries/useSettingsConfigQuery'
import {
  buildSettingsForm,
  buildSettingsRequest,
  createEmptySettingsForm,
  parseHeaders,
  type ProviderKind,
  type RoleName,
} from '@/features/settings/types'
import { LocalApiClientError } from '@/shared/api/client'
import AppCard from '@/shared/components/AppCard.vue'
import AppEmptyState from '@/shared/components/AppEmptyState.vue'
import { translateErrorCode } from '@/shared/i18n/errorMessages'
import UiButton from '@/shared/ui/UiButton.vue'
import UiSelect from '@/shared/ui/UiSelect.vue'

const { t } = useI18n()
const settingsConfigQuery = useSettingsConfigQuery()
const settingsConfigMutation = useSettingsConfigMutation()
const form = reactive(createEmptySettingsForm())
const submitError = ref<string | null>(null)
const submitSuccess = ref<string | null>(null)

const providerOptions = computed(() => [
  { value: 'openai_compatible', label: t('settings.providers.openaiCompatible') },
  { value: 'gemini', label: t('settings.providers.gemini') },
])

const roleLabels = computed<Record<RoleName, string>>(() => ({
  plan: t('settings.roles.plan'),
  runner: t('settings.roles.runner'),
  judge: t('settings.roles.judge'),
  review: t('settings.roles.review'),
  analysis: t('settings.roles.analysis'),
}))

const isBusy = computed(() => settingsConfigQuery.isFetching.value || settingsConfigMutation.isPending.value)
const loadErrorMessage = computed(() => translateUnknownError(settingsConfigQuery.error.value))

const saveDisabled = computed(() => {
  if (isBusy.value) {
    return true
  }
  return activeSectionMissingRequiredFields()
})

watch(() => settingsConfigQuery.data.value, (data) => {
  if (!data) {
    return
  }
  Object.assign(form, buildSettingsForm(data))
  submitError.value = null
}, { immediate: true })

watch(() => form.provider, (provider) => {
  if (provider === 'openai_compatible') {
    form.openai_compatible.configured = true
  }
  if (provider === 'gemini') {
    form.gemini.configured = true
  }
})

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

function activeSectionMissingRequiredFields(): boolean {
  if (form.proxy.enabled && !form.proxy.url.trim()) {
    return true
  }
  const activeSection = form.provider === 'openai_compatible' ? form.openai_compatible : form.gemini
  if (!activeSection.configured) {
    return true
  }
  if (!activeSection.model.trim()) {
    return true
  }
  if (form.provider === 'openai_compatible') {
    if (!form.openai_compatible.base_url.trim()) {
      return true
    }
    try {
      parseHeaders(form.openai_compatible.extra_headers_json)
    } catch {
      return true
    }
  }
  for (const role of ['plan', 'runner', 'judge', 'review', 'analysis'] as RoleName[]) {
    const agent = form.agents[role]
    if (!agent.enabled) {
      continue
    }
    if (!agent.provider) {
      return true
    }
    const agentSection = agent.provider === 'openai_compatible' ? agent.openai_compatible : agent.gemini
    if (!agentSection.configured || !agentSection.model.trim()) {
      return true
    }
    if (agent.provider === 'openai_compatible') {
      if (!agent.openai_compatible.base_url.trim()) {
        return true
      }
      try {
        parseHeaders(agent.openai_compatible.extra_headers_json)
      } catch {
        return true
      }
    }
  }
  return false
}

async function handleSave() {
  submitError.value = null
  submitSuccess.value = null
  try {
    const result = await settingsConfigMutation.mutateAsync(buildSettingsRequest(form))
    Object.assign(form, buildSettingsForm(result))
    submitSuccess.value = t('settings.messages.saveSuccess')
  } catch (error) {
    submitError.value = translateUnknownError(error) ?? t('settings.messages.saveFailed')
  }
}

async function handleRefresh() {
  submitError.value = null
  submitSuccess.value = null
  await settingsConfigQuery.refetch()
}

function isActiveProvider(kind: ProviderKind): boolean {
  return form.provider === kind
}
</script>

<template>
  <section class="app-page max-w-6xl">
    <AppCard class="grid gap-4">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="grid gap-1">
          <span class="text-sm text-text-secondary">{{ t('settings.fields.configPath') }}</span>
          <code class="block overflow-x-auto text-sm text-text-primary">{{ form.config_path }}</code>
        </div>
        <div class="flex flex-wrap items-center gap-2">
        <UiButton type="button" variant="secondary" :disabled="isBusy" @click="handleRefresh">
          <RefreshCw class="h-4 w-4" />
          {{ t('settings.actions.refresh') }}
        </UiButton>
        <UiButton type="button" variant="primary" :disabled="saveDisabled" @click="handleSave">
          <Save class="h-4 w-4" />
          {{ settingsConfigMutation.isPending.value ? t('settings.actions.saving') : t('settings.actions.save') }}
        </UiButton>
      </div>
      </div>
    </AppCard>

    <AppEmptyState v-if="loadErrorMessage" :title="t('settings.errorTitle')" :description="loadErrorMessage" />

    <template v-else>
      <section class="grid gap-3">
        <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <h2 class="text-lg font-semibold text-text-primary">{{ t('settings.sections.globalProvider') }}</h2>
          <div class="w-full md:w-[280px]">
            <UiSelect
              v-model="form.provider"
              :options="providerOptions"
              :placeholder="t('settings.placeholders.selectProvider')"
            />
          </div>
        </div>
        <div class="grid gap-3">
          <AppCard class="p-0">
            <ProviderSectionForm
              kind="openai_compatible"
              :section="form.openai_compatible"
              :active="isActiveProvider('openai_compatible')"
              :default-expanded="false"
            />
          </AppCard>
          <AppCard class="p-0">
            <ProviderSectionForm
              kind="gemini"
              :section="form.gemini"
              :active="isActiveProvider('gemini')"
              :default-expanded="false"
            />
          </AppCard>
        </div>
      </section>

      <section class="grid gap-3">
        <div class="grid gap-1">
          <h2 class="text-lg font-semibold text-text-primary">{{ t('settings.sections.agentOverrides') }}</h2>
        </div>

        <div class="grid gap-3">
          <AgentConfigCard
            v-for="role in ['plan', 'runner', 'judge', 'review', 'analysis']"
            :key="role"
            :role="role"
            :role-label="roleLabels[role as RoleName]"
            :config="form.agents[role as RoleName]"
          />
        </div>
      </section>

      <section class="grid gap-3">
        <div class="grid gap-1">
          <h2 class="text-lg font-semibold text-text-primary">{{ t('settings.sections.orchestration') }}</h2>
          <p class="text-sm text-text-secondary">{{ t('settings.sections.orchestrationDescription') }}</p>
        </div>
        <div class="rounded-2xl border border-border bg-surface-elevated px-4 py-4 md:px-5">
          <OrchestrationConfigForm :orchestration="form.orchestration" />
        </div>
      </section>

      <section class="grid gap-3">
        <div class="grid gap-1">
          <h2 class="text-lg font-semibold text-text-primary">{{ t('settings.sections.proxy') }}</h2>
          <p class="text-sm text-text-secondary">{{ t('settings.sections.proxyDescription') }}</p>
        </div>
        <div class="rounded-2xl border border-border bg-surface-elevated px-4 py-4 md:px-5">
          <ProxyConfigForm :proxy="form.proxy" />
        </div>
      </section>

      <section class="grid gap-3">
        <div class="grid gap-1">
          <h2 class="text-lg font-semibold text-text-primary">{{ t('settings.sections.runtime') }}</h2>
        </div>
        <div class="rounded-2xl border border-border bg-surface-elevated px-4 py-4 md:px-5">
          <RuntimeConfigForm :runtime="form.runtime" />
        </div>
      </section>

      <AppEmptyState v-if="submitError" :title="t('settings.errorTitle')" :description="submitError" />
      <div
        v-else-if="submitSuccess"
        class="rounded-2xl border border-accent/20 bg-accent/5 px-4 py-3 text-sm text-text-secondary"
      >
        {{ submitSuccess }}
      </div>
    </template>
  </section>
</template>
