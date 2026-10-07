<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { useAppsQuery } from '@/features/apps/queries/useAppsQuery'
import CloudLinkFromCloudSection from '@/features/cloud/components/CloudLinkFromCloudSection.vue'
import CloudPublishLocalSection from '@/features/cloud/components/CloudPublishLocalSection.vue'
import CloudSyncedTargetPanel from '@/features/cloud/components/CloudSyncedTargetPanel.vue'
import CloudSyncConflictModal, {
  type CloudSyncConflictDetails,
  type CloudSyncConflictKind,
} from '@/features/cloud/components/CloudSyncConflictModal.vue'
import { isCloudSessionExpiredError } from '@/features/cloud/lib/sessionExpired'
import { useCloudSessionExpiredRecovery } from '@/features/cloud/lib/useCloudSessionExpiredRecovery'
import { useCloudAppsQuery } from '@/features/cloud/queries/useCloudAppsQuery'
import { useCloudAuthWorkspacesQuery } from '@/features/cloud/queries/useCloudAuthWorkspacesQuery'
import {
  useCloudLinkActiveMutation,
  useCloudLinkDeleteMutation,
  useCloudLinkPutMutation,
} from '@/features/cloud/queries/useCloudLinkMutations'
import { useCloudLinksQuery } from '@/features/cloud/queries/useCloudLinksQuery'
import {
  useCloudSyncPublishMutation,
  useCloudSyncPullMutation,
  useCloudSyncPushMutation,
} from '@/features/cloud/queries/useCloudSyncMutations'
import { useCloudSyncStatusQuery } from '@/features/cloud/queries/useCloudSyncStatusQuery'
import { LocalApiClientError } from '@/shared/api/client'
import AppCard from '@/shared/components/AppCard.vue'
import { translateErrorCode } from '@/shared/i18n/errorMessages'

const props = defineProps<{
  authenticated: boolean
}>()

const { t } = useI18n()

const linksQuery = useCloudLinksQuery(() => props.authenticated)
const workspacesQuery = useCloudAuthWorkspacesQuery(() => props.authenticated)

const selectedWorkspaceId = ref('')
const selectedAppId = ref('')
const selectedLocalAppId = ref('')
const actionError = ref<string | null>(null)
const actionSuccess = ref<string | null>(null)
const unlinkingAppId = ref<string | null>(null)
const settingActiveAppId = ref<string | null>(null)
const lastAuthError = ref<unknown>(null)

const conflictOpen = ref(false)
const conflictKind = ref<CloudSyncConflictKind>('local_dirty')
const conflictDetails = ref<CloudSyncConflictDetails | null>(null)

const links = computed(() => linksQuery.data.value?.items ?? [])
const activeAppId = computed(() => linksQuery.data.value?.active_app_id ?? null)
const activeLink = computed(() => (
  links.value.find((item) => item.app_id === activeAppId.value) ?? links.value[0] ?? null
))
const hasActiveLink = computed(() => Boolean(activeLink.value))

const statusQuery = useCloudSyncStatusQuery(
  () => props.authenticated && hasActiveLink.value,
  () => activeLink.value?.app_id ?? null,
)
const appsQuery = useCloudAppsQuery(() => (
  props.authenticated ? (selectedWorkspaceId.value || activeLink.value?.workspace_id || null) : null
))
const localAppsQuery = useAppsQuery(computed(() => ({})))

useCloudSessionExpiredRecovery(() => workspacesQuery.error.value)
useCloudSessionExpiredRecovery(() => appsQuery.error.value)
useCloudSessionExpiredRecovery(() => statusQuery.error.value)
useCloudSessionExpiredRecovery(() => lastAuthError.value)

const putLinkMutation = useCloudLinkPutMutation()
const setActiveMutation = useCloudLinkActiveMutation()
const deleteLinkMutation = useCloudLinkDeleteMutation()
const pullMutation = useCloudSyncPullMutation()
const pushMutation = useCloudSyncPushMutation()
const publishMutation = useCloudSyncPublishMutation()

const workspaces = computed(() => workspacesQuery.data.value?.workspaces ?? [])
const apps = computed(() => appsQuery.data.value?.apps ?? [])
const localApps = computed(() => localAppsQuery.data.value ?? [])
const status = computed(() => statusQuery.data.value ?? null)

const workspaceOptions = computed(() => workspaces.value.map((item) => ({
  value: item.id,
  label: `${item.name} (${item.role})`,
})))

const appOptions = computed(() => apps.value.map((item) => ({
  value: item.app_id,
  label: `${item.app_name || item.app_id} · ${item.platform} · r${item.revision}`,
})))

const localAppOptions = computed(() => localApps.value.map((item) => ({
  value: item.app_id,
  label: `${item.app_name || item.app_id} · ${item.platform}`,
})))

const selectedWorkspace = computed(() => (
  workspaces.value.find((item) => item.id === selectedWorkspaceId.value) ?? null
))

const canPublishAsAdmin = computed(() => {
  const role = selectedWorkspace.value?.role
  return role === 'owner' || role === 'admin'
})

const isBusy = computed(
  () =>
    putLinkMutation.isPending.value
    || setActiveMutation.isPending.value
    || deleteLinkMutation.isPending.value
    || pullMutation.isPending.value
    || pushMutation.isPending.value
    || publishMutation.isPending.value,
)

const canForcePush = computed(() => Boolean(status.value?.can_force_push))

watch(
  [() => props.authenticated, activeLink],
  () => {
    if (!props.authenticated) {
      selectedWorkspaceId.value = ''
      selectedAppId.value = ''
      selectedLocalAppId.value = ''
      return
    }
    if (activeLink.value && !selectedWorkspaceId.value) {
      selectedWorkspaceId.value = activeLink.value.workspace_id
    }
  },
  { immediate: true },
)

watch(selectedWorkspaceId, (workspaceId, previous) => {
  if (workspaceId !== previous) {
    selectedAppId.value = ''
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

function captureActionError(error: unknown, fallback: string): void {
  if (isCloudSessionExpiredError(error)) {
    lastAuthError.value = error
    actionError.value = t('cloud.auth.sessionExpired')
    return
  }
  lastAuthError.value = null
  actionError.value = translateUnknownError(error) ?? fallback
}

function asConflictDetails(details: Record<string, unknown> | undefined): CloudSyncConflictDetails {
  if (!details) {
    return {}
  }
  return {
    base_revision: typeof details.base_revision === 'number' ? details.base_revision : null,
    cloud_revision: typeof details.cloud_revision === 'number' ? details.cloud_revision : null,
    expected_revision: typeof details.expected_revision === 'number' ? details.expected_revision : null,
    current_revision: typeof details.current_revision === 'number' ? details.current_revision : null,
    local_content_hash: typeof details.local_content_hash === 'string' ? details.local_content_hash : null,
    cloud_content_hash: typeof details.cloud_content_hash === 'string' ? details.cloud_content_hash : null,
  }
}

function openConflict(kind: CloudSyncConflictKind, details: Record<string, unknown> | undefined) {
  conflictKind.value = kind
  conflictDetails.value = asConflictDetails(details)
  conflictOpen.value = true
}

function closeConflict() {
  conflictOpen.value = false
  conflictDetails.value = null
}

async function handleLink() {
  actionError.value = null
  actionSuccess.value = null
  if (!selectedWorkspaceId.value || !selectedAppId.value) {
    actionError.value = t('cloud.sync.linkIncomplete')
    return
  }
  try {
    await putLinkMutation.mutateAsync({
      workspace_id: selectedWorkspaceId.value,
      app_id: selectedAppId.value,
      workspace_name: selectedWorkspace.value?.name ?? null,
      role: selectedWorkspace.value?.role ?? null,
    })
    actionSuccess.value = t('cloud.sync.linkSuccess')
  }
  catch (error) {
    captureActionError(error, t('cloud.sync.linkFailed'))
  }
}

async function handleSetActive(appId: string) {
  actionError.value = null
  actionSuccess.value = null
  settingActiveAppId.value = appId
  try {
    await setActiveMutation.mutateAsync({ app_id: appId })
  }
  catch (error) {
    captureActionError(error, t('cloud.sync.setActiveFailed'))
  }
  finally {
    settingActiveAppId.value = null
  }
}

async function handleUnlink(appId: string) {
  actionError.value = null
  actionSuccess.value = null
  unlinkingAppId.value = appId
  try {
    await deleteLinkMutation.mutateAsync(appId)
    if (selectedAppId.value === appId) {
      selectedAppId.value = ''
    }
    actionSuccess.value = t('cloud.sync.unlinkSuccess')
  }
  catch (error) {
    captureActionError(error, t('cloud.sync.unlinkFailed'))
  }
  finally {
    unlinkingAppId.value = null
  }
}

async function handlePull(force = false) {
  actionError.value = null
  actionSuccess.value = null
  const appId = activeLink.value?.app_id ?? null
  try {
    const result = await pullMutation.mutateAsync({ force, appId })
    closeConflict()
    actionSuccess.value = t('cloud.sync.pullSuccess', {
      revision: result.revision,
      written: result.plans_written,
      deleted: result.plans_deleted,
    })
  }
  catch (error) {
    if (error instanceof LocalApiClientError && error.code === 'local_sync_conflict') {
      openConflict('local_dirty', error.details)
      return
    }
    captureActionError(error, t('cloud.sync.pullFailed'))
  }
}

async function handlePush(force = false) {
  actionError.value = null
  actionSuccess.value = null
  const appId = activeLink.value?.app_id ?? null
  try {
    const result = await pushMutation.mutateAsync({ force, appId })
    closeConflict()
    actionSuccess.value = t('cloud.sync.pushSuccess', {
      revision: result.revision,
      action: result.action,
    })
  }
  catch (error) {
    if (error instanceof LocalApiClientError && error.code === 'sync_revision_conflict') {
      openConflict('revision', error.details)
      return
    }
    captureActionError(error, t('cloud.sync.pushFailed'))
  }
}

async function handlePullThenPush() {
  actionError.value = null
  actionSuccess.value = null
  const appId = activeLink.value?.app_id ?? null
  try {
    await pullMutation.mutateAsync({ force: false, appId })
    const result = await pushMutation.mutateAsync({ force: false, appId })
    closeConflict()
    actionSuccess.value = t('cloud.sync.pushSuccess', {
      revision: result.revision,
      action: result.action,
    })
  }
  catch (error) {
    if (error instanceof LocalApiClientError && error.code === 'local_sync_conflict') {
      openConflict('local_dirty', error.details)
      return
    }
    if (error instanceof LocalApiClientError && error.code === 'sync_revision_conflict') {
      openConflict('revision', error.details)
      return
    }
    captureActionError(error, t('cloud.sync.pushFailed'))
  }
}

async function handlePublish() {
  actionError.value = null
  actionSuccess.value = null
  if (!selectedWorkspaceId.value || !selectedLocalAppId.value) {
    actionError.value = t('cloud.sync.publishIncomplete')
    return
  }
  try {
    const result = await publishMutation.mutateAsync({
      workspace_id: selectedWorkspaceId.value,
      app_id: selectedLocalAppId.value,
      workspace_name: selectedWorkspace.value?.name ?? null,
    })
    actionSuccess.value = t('cloud.sync.publishSuccess', {
      appId: result.app_id,
      revision: result.revision,
      shellHint: result.shell_created
        ? t('cloud.sync.publishSuccessShellCreated')
        : t('cloud.sync.publishSuccessShellExisting'),
    })
  }
  catch (error) {
    captureActionError(error, t('cloud.sync.publishFailed'))
  }
}
</script>

<template>
  <AppCard v-if="authenticated" class="grid gap-5">
    <div class="grid gap-1">
      <h2 class="text-lg font-semibold text-text-primary">{{ t('cloud.sync.title') }}</h2>
      <p class="text-sm text-text-secondary">{{ t('cloud.sync.description') }}</p>
    </div>

    <div
      v-if="actionSuccess"
      class="rounded-lg border border-border-muted bg-surface-muted px-3 py-2 text-sm text-text-secondary"
    >
      {{ actionSuccess }}
    </div>
    <div
      v-if="actionError"
      class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
    >
      {{ actionError }}
    </div>
    <div
      v-if="linksQuery.error.value"
      class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
    >
      {{ translateUnknownError(linksQuery.error.value) }}
    </div>

    <CloudSyncedTargetPanel
      :links="links"
      :active-app-id="activeLink?.app_id ?? null"
      :status="status"
      :status-loading="statusQuery.isFetching.value"
      :status-error="translateUnknownError(statusQuery.error.value)"
      :busy="isBusy"
      :pulling="pullMutation.isPending.value"
      :pushing="pushMutation.isPending.value"
      :unlinking-app-id="unlinkingAppId"
      :setting-active-app-id="settingActiveAppId"
      @pull="handlePull(false)"
      @push="handlePush(false)"
      @unlink="handleUnlink"
      @set-active="handleSetActive"
    />

    <div
      class="border-t border-border-muted"
      aria-hidden="true"
    />

    <CloudLinkFromCloudSection
      :workspace-id="selectedWorkspaceId"
      :app-id="selectedAppId"
      :workspace-options="workspaceOptions"
      :app-options="appOptions"
      :workspaces-loading="workspacesQuery.isFetching.value"
      :apps-loading="appsQuery.isFetching.value"
      :workspace-count="workspaces.length"
      :app-count="apps.length"
      :busy="isBusy"
      :linking="putLinkMutation.isPending.value"
      :show-cancel="false"
      @update:workspace-id="selectedWorkspaceId = $event"
      @update:app-id="selectedAppId = $event"
      @link="handleLink"
    />

    <div class="border-t border-border-muted" aria-hidden="true" />

    <CloudPublishLocalSection
      v-model:workspace-id="selectedWorkspaceId"
      v-model:local-app-id="selectedLocalAppId"
      :workspace-options="workspaceOptions"
      :local-app-options="localAppOptions"
      :workspaces-loading="workspacesQuery.isFetching.value"
      :local-apps-loading="localAppsQuery.isFetching.value"
      :workspace-count="workspaces.length"
      :local-app-count="localApps.length"
      :can-publish-as-admin="canPublishAsAdmin"
      :busy="isBusy"
      :publishing="publishMutation.isPending.value"
      @publish="handlePublish"
    />

    <CloudSyncConflictModal
      :open="conflictOpen"
      :kind="conflictKind"
      :details="conflictDetails"
      :can-force-push="canForcePush"
      :busy="isBusy"
      @close="closeConflict"
      @force-pull="handlePull(true)"
      @pull-then-push="handlePullThenPush"
      @force-push="handlePush(true)"
    />
  </AppCard>
</template>
