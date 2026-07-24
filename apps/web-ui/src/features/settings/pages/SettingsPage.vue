<script setup lang="ts">
import { Save, RefreshCw } from '@lucide/vue'
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import AgentConfigCard from '@/features/settings/components/AgentConfigCard.vue'
import OrchestrationConfigForm from '@/features/settings/components/OrchestrationConfigForm.vue'
import ProxyConfigForm from '@/features/settings/components/ProxyConfigForm.vue'
import RuntimeConfigForm from '@/features/settings/components/RuntimeConfigForm.vue'
import TestEnvConfigForm from '@/features/settings/components/TestEnvConfigForm.vue'
import ProviderSectionForm from '@/features/settings/components/ProviderSectionForm.vue'
import { useSettingsConfigMutation } from '@/features/settings/queries/useSettingsConfigMutation'
import { useSettingsConfigQuery } from '@/features/settings/queries/useSettingsConfigQuery'
import {
  buildSettingsForm,
  buildSettingsRequest,
  createEmptySettingsForm,
  isActiveProviderSectionMissingRequiredFields,
  type ProviderKind,
  type RoleName,
} from '@/features/settings/types'
import { LocalApiClientError } from '@/shared/api/client'
import AppCard from '@/shared/components/AppCard.vue'
import AppEmptyState from '@/shared/components/AppEmptyState.vue'
import { translateErrorCode } from '@/shared/i18n/errorMessages'
import UiButton from '@/shared/ui/UiButton.vue'
import UiField from '@/shared/ui/UiField.vue'
import UiInput from '@/shared/ui/UiInput.vue'
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
  if (
    form.ios_bridge.sudo_enabled
    && !form.ios_bridge.sudo_password.trim()
    && !form.ios_bridge.sudo_password_configured
  ) {
    return true
  }

  if (
    form.provider === 'openai_compatible'
      ? isActiveProviderSectionMissingRequiredFields('openai_compatible', form.openai_compatible)
      : isActiveProviderSectionMissingRequiredFields('gemini', form.gemini)
  ) {
    return true
  }

  for (const role of ['plan', 'runner', 'judge', 'review', 'analysis'] as RoleName[]) {
    const agent = form.agents[role]
    if (!agent.enabled) {
      continue
    }
    if (!agent.provider) {
      return true
    }
    if (
      agent.provider === 'openai_compatible'
        ? isActiveProviderSectionMissingRequiredFields('openai_compatible', agent.openai_compatible)
        : isActiveProviderSectionMissingRequiredFields('gemini', agent.gemini)
    ) {
      return true
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
          <div class="w-full md:w-[320px]">
            <UiField
              :label="t('settings.fields.provider')"
              required
              :description="t('settings.fieldDescriptions.provider')"
            >
              <UiSelect
                v-model="form.provider"
                :options="providerOptions"
                :placeholder="t('settings.placeholders.selectProvider')"
              />
            </UiField>
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
          <h2 class="text-lg font-semibold text-text-primary">{{ t('settings.sections.iosBridge') }}</h2>
          <p class="text-sm text-text-secondary">{{ t('settings.sections.iosBridgeDescription') }}</p>
        </div>
        <div class="rounded-2xl border border-border bg-surface-elevated px-4 py-4 md:px-5">
          <div class="grid gap-4">
            <UiField
              :label="t('settings.fields.iosBridgeSudoEnabled')"
              optional
              :description="t('settings.fieldDescriptions.iosBridgeSudoEnabled')"
            >
              <label class="flex min-h-11 items-center gap-2 rounded-xl border border-border bg-surface-muted/35 px-3.5 text-sm text-text-secondary">
                <input v-model="form.ios_bridge.sudo_enabled" type="checkbox" class="h-4 w-4 rounded border-border">
                {{ t('settings.iosBridge.enableSudoToggle') }}
              </label>
            </UiField>

            <UiField
              :label="t('settings.fields.iosBridgeSudoPassword')"
              :required="form.ios_bridge.sudo_enabled && !form.ios_bridge.sudo_password_configured"
              :optional="!form.ios_bridge.sudo_enabled || form.ios_bridge.sudo_password_configured"
              :description="t('settings.fieldDescriptions.iosBridgeSudoPassword', {
                requirement: form.ios_bridge.sudo_enabled
                  ? t('settings.fieldDescriptions.common.enabledRequired')
                  : t('settings.fieldDescriptions.common.disabledOptional'),
                preserveRule: form.ios_bridge.sudo_password_configured
                  ? t('settings.fieldDescriptions.common.secretConfiguredKeep')
                  : t('settings.fieldDescriptions.common.secretEmptySkipped'),
              })"
            >
              <UiInput
                v-model="form.ios_bridge.sudo_password"
                type="password"
                :placeholder="form.ios_bridge.sudo_password_configured
                  ? t('settings.fields.apiKeyConfigured')
                  : t('settings.placeholders.iosBridgeSudoPassword')"
              />
            </UiField>
          </div>
        </div>
      </section>

      <section class="grid gap-3">
        <div class="grid gap-1">
          <h2 class="text-lg font-semibold text-text-primary">{{ t('settings.sections.testEnv') }}</h2>
          <p class="text-sm text-text-secondary">{{ t('settings.sections.testEnvDescription') }}</p>
        </div>
        <div class="rounded-2xl border border-border bg-surface-elevated px-4 py-4 md:px-5">
          <TestEnvConfigForm :test-env="form.test_env" />
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
