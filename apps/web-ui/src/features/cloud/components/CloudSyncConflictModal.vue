<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import UiButton from '@/shared/ui/UiButton.vue'

export type CloudSyncConflictKind = 'local_dirty' | 'revision'

export type CloudSyncConflictDetails = {
  base_revision?: number | null
  cloud_revision?: number | null
  expected_revision?: number | null
  current_revision?: number | null
  local_content_hash?: string | null
  cloud_content_hash?: string | null
}

const props = defineProps<{
  open: boolean
  kind: CloudSyncConflictKind
  details: CloudSyncConflictDetails | null
  canForcePush: boolean
  busy: boolean
}>()

const emit = defineEmits<{
  close: []
  'force-pull': []
  'pull-then-push': []
  'force-push': []
}>()

const { t } = useI18n()

const title = computed(() => (
  props.kind === 'local_dirty'
    ? t('cloud.conflict.localDirtyTitle')
    : t('cloud.conflict.revisionTitle')
))

const description = computed(() => (
  props.kind === 'local_dirty'
    ? t('cloud.conflict.localDirtyDescription')
    : t('cloud.conflict.revisionDescription')
))

function handleClose() {
  if (props.busy) {
    return
  }
  emit('close')
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="fixed inset-0 z-[80] flex items-center justify-center px-4">
      <button
        type="button"
        class="absolute inset-0 bg-surface-overlay/60 backdrop-blur-sm"
        :disabled="busy"
        @click="handleClose"
      />
      <div class="relative z-[81] grid w-full max-w-lg gap-5 rounded-2xl border border-border bg-surface-default p-6 shadow-panel">
        <div class="grid gap-1">
          <h2 class="text-lg font-semibold text-text-primary">{{ title }}</h2>
          <p class="text-sm text-text-secondary">{{ description }}</p>
        </div>

        <dl v-if="details" class="grid gap-2 rounded-lg border border-border-muted bg-surface-muted px-3 py-3 text-sm">
          <template v-if="kind === 'local_dirty'">
            <div class="flex flex-wrap justify-between gap-2">
              <dt class="text-text-secondary">{{ t('cloud.conflict.baseRevision') }}</dt>
              <dd class="font-medium text-text-primary">{{ details.base_revision ?? '—' }}</dd>
            </div>
            <div class="flex flex-wrap justify-between gap-2">
              <dt class="text-text-secondary">{{ t('cloud.conflict.cloudRevision') }}</dt>
              <dd class="font-medium text-text-primary">{{ details.cloud_revision ?? '—' }}</dd>
            </div>
          </template>
          <template v-else>
            <div class="flex flex-wrap justify-between gap-2">
              <dt class="text-text-secondary">{{ t('cloud.conflict.expectedRevision') }}</dt>
              <dd class="font-medium text-text-primary">{{ details.expected_revision ?? '—' }}</dd>
            </div>
            <div class="flex flex-wrap justify-between gap-2">
              <dt class="text-text-secondary">{{ t('cloud.conflict.currentRevision') }}</dt>
              <dd class="font-medium text-text-primary">{{ details.current_revision ?? '—' }}</dd>
            </div>
          </template>
        </dl>

        <p v-if="kind === 'revision' && canForcePush" class="text-sm text-text-secondary">
          {{ t('cloud.conflict.forcePushWarning') }}
        </p>

        <div class="flex flex-wrap justify-end gap-3">
          <UiButton type="button" variant="secondary" :disabled="busy" @click="handleClose">
            {{ t('cloud.conflict.cancel') }}
          </UiButton>
          <UiButton
            v-if="kind === 'local_dirty'"
            type="button"
            variant="primary"
            :disabled="busy"
            @click="emit('force-pull')"
          >
            {{ t('cloud.conflict.discardLocal') }}
          </UiButton>
          <template v-else>
            <UiButton type="button" variant="primary" :disabled="busy" @click="emit('pull-then-push')">
              {{ t('cloud.conflict.pullThenPush') }}
            </UiButton>
            <UiButton
              v-if="canForcePush"
              type="button"
              variant="secondary"
              :disabled="busy"
              @click="emit('force-push')"
            >
              {{ t('cloud.conflict.forcePush') }}
            </UiButton>
          </template>
        </div>
      </div>
    </div>
  </Teleport>
</template>
