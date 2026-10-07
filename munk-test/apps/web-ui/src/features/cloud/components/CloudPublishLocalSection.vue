<script setup lang="ts">
import { Upload } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import UiButton from '@/shared/ui/UiButton.vue'
import UiField from '@/shared/ui/UiField.vue'
import UiSelect from '@/shared/ui/UiSelect.vue'

defineProps<{
  workspaceId: string
  localAppId: string
  workspaceOptions: Array<{ value: string, label: string }>
  localAppOptions: Array<{ value: string, label: string }>
  workspacesLoading: boolean
  localAppsLoading: boolean
  workspaceCount: number
  localAppCount: number
  canPublishAsAdmin: boolean
  busy: boolean
  publishing: boolean
}>()

const emit = defineEmits<{
  'update:workspaceId': [value: string]
  'update:localAppId': [value: string]
  publish: []
}>()

const { t } = useI18n()
</script>

<template>
  <section class="grid gap-3">
    <div class="grid gap-1">
      <h3 class="text-sm font-medium text-text-primary">{{ t('cloud.sync.publishTitle') }}</h3>
      <p class="text-sm text-text-secondary">{{ t('cloud.sync.publishDescription') }}</p>
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
      <UiField :label="t('cloud.sync.selectLocalApp')">
        <UiSelect
          :model-value="localAppId"
          :options="localAppOptions"
          :placeholder="t('cloud.sync.selectLocalAppPlaceholder')"
          :disabled="localAppsLoading || localAppCount === 0 || busy"
          @update:model-value="emit('update:localAppId', $event)"
        />
      </UiField>
      <div class="md:col-span-2">
        <UiButton
          type="button"
          variant="primary"
          :disabled="busy || !workspaceId || !localAppId || !canPublishAsAdmin"
          @click="emit('publish')"
        >
          <Upload class="h-4 w-4" />
          {{ publishing ? t('cloud.sync.publishing') : t('cloud.sync.publish') }}
        </UiButton>
      </div>
      <p
        v-if="workspaceId && !canPublishAsAdmin"
        class="text-sm text-text-secondary md:col-span-2"
      >
        {{ t('cloud.sync.publishAdminHint') }}
      </p>
      <p
        v-else-if="localAppCount === 0 && !localAppsLoading"
        class="text-sm text-text-secondary md:col-span-2"
      >
        {{ t('cloud.sync.noLocalApps') }}
      </p>
    </div>
  </section>
</template>
