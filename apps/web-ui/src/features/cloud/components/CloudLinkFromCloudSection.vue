<script setup lang="ts">
import { Link2 } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import UiButton from '@/shared/ui/UiButton.vue'
import UiField from '@/shared/ui/UiField.vue'
import UiSelect from '@/shared/ui/UiSelect.vue'

defineProps<{
  workspaceId: string
  appId: string
  workspaceOptions: Array<{ value: string, label: string }>
  appOptions: Array<{ value: string, label: string }>
  workspacesLoading: boolean
  appsLoading: boolean
  workspaceCount: number
  appCount: number
  busy: boolean
  linking: boolean
  showCancel: boolean
}>()

const emit = defineEmits<{
  'update:workspaceId': [value: string]
  'update:appId': [value: string]
  link: []
  cancel: []
}>()

const { t } = useI18n()
</script>

<template>
  <section class="grid gap-3">
    <div class="grid gap-1">
      <h3 class="text-sm font-medium text-text-primary">{{ t('cloud.sync.linkFromCloudTitle') }}</h3>
      <p class="text-sm text-text-secondary">{{ t('cloud.sync.linkHint') }}</p>
    </div>

    <div class="grid gap-3 md:grid-cols-2">
      <UiField :label="t('cloud.sync.selectWorkspace')">
        <UiSelect
          :model-value="workspaceId"
          :options="workspaceOptions"
          :placeholder="t('cloud.sync.selectWorkspacePlaceholder')"
          :disabled="workspacesLoading || workspaceCount === 0 || busy"
          @update:model-value="emit('update:workspaceId', $event)"
        />
      </UiField>
      <UiField :label="t('cloud.sync.selectApp')">
        <UiSelect
          :model-value="appId"
          :options="appOptions"
          :placeholder="t('cloud.sync.selectAppPlaceholder')"
          :disabled="!workspaceId || appsLoading || appCount === 0 || busy"
          @update:model-value="emit('update:appId', $event)"
        />
      </UiField>
      <div class="flex flex-wrap items-center gap-2 md:col-span-2">
        <UiButton
          type="button"
          variant="primary"
          :disabled="busy || !workspaceId || !appId"
          @click="emit('link')"
        >
          <Link2 class="h-4 w-4" />
          {{ linking ? t('cloud.sync.linking') : t('cloud.sync.link') }}
        </UiButton>
        <UiButton
          v-if="showCancel"
          type="button"
          variant="secondary"
          :disabled="busy"
          @click="emit('cancel')"
        >
          {{ t('cloud.sync.cancelSwitch') }}
        </UiButton>
      </div>
      <p v-if="workspaceCount === 0 && !workspacesLoading" class="text-sm text-text-secondary md:col-span-2">
        {{ t('cloud.auth.noWorkspaces') }}
      </p>
      <p
        v-else-if="workspaceId && appCount === 0 && !appsLoading"
        class="text-sm text-text-secondary md:col-span-2"
      >
        {{ t('cloud.sync.noApps') }}
      </p>
    </div>
  </section>
</template>
