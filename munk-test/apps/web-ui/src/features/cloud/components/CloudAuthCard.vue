<script setup lang="ts">
import { Cloud, LogIn, LogOut } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import { isCloudSessionExpiredError } from '@/features/cloud/lib/sessionExpired'
import { useCloudSessionExpiredRecovery } from '@/features/cloud/lib/useCloudSessionExpiredRecovery'
import { useCloudAuthLoginMutation, useCloudAuthLogoutMutation } from '@/features/cloud/queries/useCloudAuthMutations'
import { useCloudAuthSessionQuery } from '@/features/cloud/queries/useCloudAuthSessionQuery'
import { useCloudAuthWorkspacesQuery } from '@/features/cloud/queries/useCloudAuthWorkspacesQuery'
import { LocalApiClientError } from '@/shared/api/client'
import AppCard from '@/shared/components/AppCard.vue'
import { translateErrorCode } from '@/shared/i18n/errorMessages'
import UiButton from '@/shared/ui/UiButton.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const sessionQuery = useCloudAuthSessionQuery()
const loginMutation = useCloudAuthLoginMutation()
const logoutMutation = useCloudAuthLogoutMutation()

const actionError = ref<string | null>(null)
const bannerMessage = ref<string | null>(null)
const sessionExpiredNotice = ref(false)

const authenticated = computed(() => Boolean(sessionQuery.data.value?.authenticated))
const workspacesQuery = useCloudAuthWorkspacesQuery(authenticated)

useCloudSessionExpiredRecovery(
  () => workspacesQuery.error.value,
  () => {
    sessionExpiredNotice.value = true
  },
)

const isBusy = computed(
  () =>
    sessionQuery.isFetching.value
    || loginMutation.isPending.value
    || logoutMutation.isPending.value,
)

const displayName = computed(() => {
  const user = sessionQuery.data.value?.user
  if (!user) {
    return ''
  }
  return user.display_name || user.email || user.id
})

const workspaces = computed(() => workspacesQuery.data.value?.workspaces ?? [])

watch(
  () => route.query.cloud,
  async (cloud) => {
    if (typeof cloud !== 'string') {
      return
    }
    if (cloud === 'connected') {
      bannerMessage.value = t('cloud.auth.connected')
      actionError.value = null
      sessionExpiredNotice.value = false
      await sessionQuery.refetch()
      await workspacesQuery.refetch()
    }
    else if (cloud === 'error') {
      const message = typeof route.query.message === 'string' ? route.query.message : 'cloud_auth_failed'
      bannerMessage.value = null
      actionError.value = t('cloud.auth.callbackError', { message })
    }
    const nextQuery = { ...route.query }
    delete nextQuery.cloud
    delete nextQuery.message
    await router.replace({ query: nextQuery })
  },
  { immediate: true },
)

watch(authenticated, (value) => {
  if (value) {
    sessionExpiredNotice.value = false
  }
})

function translateUnknownError(error: unknown): string | null {
  if (!error) {
    return null
  }
  if (isCloudSessionExpiredError(error)) {
    return t('cloud.auth.sessionExpired')
  }
  if (error instanceof LocalApiClientError) {
    return translateErrorCode(error.code, error.message)
  }
  if (error instanceof Error) {
    return error.message
  }
  return String(error)
}

async function handleLogin() {
  actionError.value = null
  bannerMessage.value = null
  sessionExpiredNotice.value = false
  try {
    const result = await loginMutation.mutateAsync()
    window.location.assign(result.authorize_url)
  }
  catch (error) {
    actionError.value = translateUnknownError(error) ?? t('cloud.auth.loginFailed')
  }
}

async function handleLogout() {
  actionError.value = null
  bannerMessage.value = null
  sessionExpiredNotice.value = false
  try {
    await logoutMutation.mutateAsync()
    bannerMessage.value = t('cloud.auth.loggedOut')
  }
  catch (error) {
    actionError.value = translateUnknownError(error) ?? t('cloud.auth.logoutFailed')
  }
}
</script>

<template>
  <AppCard class="grid gap-4">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div class="grid gap-1">
        <div class="flex items-center gap-2 text-lg font-semibold text-text-primary">
          <Cloud class="h-5 w-5" />
          <span>{{ t('cloud.auth.title') }}</span>
        </div>
        <p class="text-sm text-text-secondary">
          {{ t('cloud.auth.description') }}
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <UiButton
          v-if="!authenticated"
          type="button"
          variant="primary"
          :disabled="isBusy"
          @click="handleLogin"
        >
          <LogIn class="h-4 w-4" />
          {{ loginMutation.isPending.value ? t('cloud.auth.signingIn') : t('cloud.auth.signIn') }}
        </UiButton>
        <UiButton
          v-else
          type="button"
          variant="secondary"
          :disabled="isBusy"
          @click="handleLogout"
        >
          <LogOut class="h-4 w-4" />
          {{ logoutMutation.isPending.value ? t('cloud.auth.signingOut') : t('cloud.auth.signOut') }}
        </UiButton>
      </div>
    </div>

    <div
      v-if="bannerMessage"
      class="rounded-lg border border-border-muted bg-surface-muted px-3 py-2 text-sm text-text-secondary"
    >
      {{ bannerMessage }}
    </div>
    <div
      v-if="sessionExpiredNotice && !authenticated"
      class="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900"
    >
      {{ t('cloud.auth.sessionExpired') }}
    </div>
    <div
      v-if="actionError"
      class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
    >
      {{ actionError }}
    </div>
    <div
      v-if="sessionQuery.error.value"
      class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
    >
      {{ translateUnknownError(sessionQuery.error.value) }}
    </div>
    <div
      v-else-if="workspacesQuery.error.value && authenticated"
      class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
    >
      {{ translateUnknownError(workspacesQuery.error.value) }}
    </div>

    <div v-if="authenticated" class="grid gap-3">
      <div class="grid gap-1 text-sm">
        <span class="text-text-secondary">{{ t('cloud.auth.signedInAs') }}</span>
        <span class="font-medium text-text-primary">{{ displayName }}</span>
        <span v-if="sessionQuery.data.value?.user?.email" class="text-text-secondary">
          {{ sessionQuery.data.value.user.email }}
        </span>
      </div>

      <div class="grid gap-2">
        <span class="text-sm font-medium text-text-primary">{{ t('cloud.auth.workspaces') }}</span>
        <p v-if="workspacesQuery.isLoading.value" class="text-sm text-text-secondary">
          {{ t('common.loading') }}
        </p>
        <p v-else-if="workspaces.length === 0" class="text-sm text-text-secondary">
          {{ t('cloud.auth.noWorkspaces') }}
        </p>
        <ul v-else class="grid gap-2">
          <li
            v-for="workspace in workspaces"
            :key="workspace.id"
            class="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border-muted px-3 py-2 text-sm"
          >
            <span class="font-medium text-text-primary">{{ workspace.name }}</span>
            <span class="text-text-secondary">{{ workspace.role }} · {{ workspace.slug }}</span>
          </li>
        </ul>
      </div>
    </div>

    <p v-else class="text-sm text-text-secondary">
      {{ t('cloud.auth.signedOutHint') }}
    </p>
  </AppCard>
</template>
