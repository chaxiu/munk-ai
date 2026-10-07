<script setup lang="ts">
import { Info } from '@lucide/vue'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { LocalApiClientError } from '@/shared/api/client'
import { getOperationArtifactContent, type RunArtifactItemData } from '@/shared/api/operations'
import { translateErrorCode } from '@/shared/i18n/errorMessages'
import { isImageArtifact } from '@/features/runs/lib/runMappers'

type ArtifactInfoEntry = {
  label: string
  value: string
}

const props = defineProps<{
  operationId: string
  artifact: RunArtifactItemData
}>()
const emit = defineEmits<{
  (event: 'close'): void
}>()

const { t } = useI18n()

const previewText = ref<string | null>(null)
const previewTextLoading = ref(false)
const previewTextMeta = ref<{ truncated: boolean, mediaType: string | null } | null>(null)
const isInfoOpen = ref(false)

function buildArtifactInfoEntries(entries: Array<{ label: string, value: string | null | undefined }>): ArtifactInfoEntry[] {
  return entries.flatMap((entry) => {
    const value = entry.value?.trim()
    return value ? [{ label: entry.label, value }] : []
  })
}

const artifactInfo = computed<ArtifactInfoEntry[]>(() => buildArtifactInfoEntries([
  { label: t('artifactPreview.fields.name'), value: props.artifact.label },
  { label: t('artifactPreview.fields.kind'), value: props.artifact.kind },
  { label: t('artifactPreview.fields.role'), value: props.artifact.role },
  { label: t('artifactPreview.fields.scope'), value: props.artifact.scope },
  { label: t('artifactPreview.fields.mediaType'), value: props.artifact.media_type ?? previewTextMeta.value?.mediaType ?? null },
  { label: t('artifactPreview.fields.path'), value: props.artifact.path },
]))

watch(() => props.artifact, async (artifact) => {
  isInfoOpen.value = false
  previewText.value = null
  previewTextMeta.value = null
  if (!artifact || isImageArtifact(artifact) || !artifact.content_url) {
    previewTextLoading.value = false
    return
  }
  previewTextLoading.value = true
  try {
    const response = await getOperationArtifactContent(props.operationId, artifact.artifact_id, { maxBytes: 65536 })
    previewText.value = response.content
    previewTextMeta.value = {
      truncated: response.truncated,
      mediaType: response.media_type ?? null,
    }
  } catch (error) {
    if (error instanceof LocalApiClientError) {
      previewText.value = translateErrorCode(error.code, error.message)
    } else if (error instanceof Error) {
      previewText.value = error.message
    } else {
      previewText.value = String(error)
    }
  } finally {
    previewTextLoading.value = false
  }
}, { immediate: true })

function closeModal() {
  emit('close')
}

function handleWindowKeydown(event: KeyboardEvent) {
  if (event.key !== 'Escape') {
    return
  }
  event.preventDefault()
  closeModal()
}

onMounted(() => {
  window.addEventListener('keydown', handleWindowKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleWindowKeydown)
})
</script>

<template>
  <Teleport to="body">
    <div
      class="artifact-preview-modal"
      data-testid="artifact-preview-modal"
      role="dialog"
      aria-modal="true"
      :aria-label="t('artifactPreview.dialogTitle')"
    >
      <button
        type="button"
        class="artifact-preview-backdrop"
        data-testid="artifact-preview-backdrop"
        :aria-label="t('artifactPreview.close')"
        @click="closeModal"
      />
      <div class="artifact-preview-card">
        <div class="artifact-preview-header">
          <div class="artifact-preview-meta">
            <strong>{{ t('artifactPreview.dialogTitle') }}</strong>
            <p class="muted artifact-preview-name">{{ artifact.label }}</p>
          </div>
          <div class="artifact-preview-header-actions">
            <div v-if="artifactInfo.length > 0" class="artifact-info-popover">
              <button
                type="button"
                class="secondary-button icon-button artifact-info-trigger"
                data-testid="artifact-preview-info-toggle"
                :aria-expanded="isInfoOpen"
                :aria-label="t('artifactPreview.infoLabel')"
                :title="t('artifactPreview.infoLabel')"
                @click="isInfoOpen = !isInfoOpen"
              >
                <Info :size="16" aria-hidden="true" />
                <span class="sr-only">{{ t('artifactPreview.infoLabel') }}</span>
              </button>
              <div v-if="isInfoOpen" class="artifact-info-card" data-testid="artifact-preview-info-panel">
                <div class="artifact-info-section">
                  <strong>{{ t('artifactPreview.sourceArtifactTitle') }}</strong>
                  <dl class="artifact-info-list">
                    <template v-for="entry in artifactInfo" :key="entry.label">
                      <dt>{{ entry.label }}</dt>
                      <dd>{{ entry.value }}</dd>
                    </template>
                  </dl>
                </div>
              </div>
            </div>
            <button
              type="button"
              class="secondary-button artifact-preview-close"
              data-testid="artifact-preview-close"
              @click="closeModal"
            >
              {{ t('artifactPreview.close') }}
            </button>
          </div>
        </div>
        <div class="artifact-preview-body">
          <div v-if="isImageArtifact(artifact) && artifact.download_url" class="artifact-preview-image-frame">
            <img
              class="preview-image artifact-preview-image"
              :src="artifact.download_url"
              :alt="artifact.label"
            >
          </div>
          <template v-else>
            <p v-if="previewTextLoading" class="muted">{{ t('common.loading') }}</p>
            <p v-else-if="!artifact.content_url" class="muted">{{ t('artifactPreview.unsupported') }}</p>
            <div v-else class="artifact-preview-content">
              <p v-if="previewTextMeta?.truncated" class="muted">{{ t('artifactPreview.truncated') }}</p>
              <pre>{{ previewText }}</pre>
            </div>
          </template>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.artifact-preview-modal {
  position: fixed;
  inset: 0;
  z-index: 90;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.artifact-preview-backdrop {
  position: absolute;
  inset: 0;
  border: 0;
  background: color-mix(in srgb, var(--surface-overlay) 70%, transparent);
}

.artifact-preview-card,
.artifact-preview-header,
.artifact-preview-body,
.artifact-preview-content,
.artifact-preview-meta {
  display: grid;
  gap: 12px;
  min-width: 0;
}

.artifact-preview-card {
  position: relative;
  z-index: 1;
  width: min(1080px, 100%);
  height: min(88vh, 900px);
  padding: 20px;
  border-radius: 16px;
  border: 1px solid var(--border-default);
  background: var(--surface-default);
  box-shadow: 0 24px 60px color-mix(in srgb, black 20%, transparent);
  overflow: hidden;
  grid-template-rows: auto minmax(0, 1fr);
}

.artifact-preview-header {
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: start;
}

.artifact-preview-header-actions {
  position: relative;
  display: flex;
  align-items: start;
  gap: 8px;
}

.artifact-preview-body {
  display: grid;
  grid-template-rows: minmax(0, 1fr);
  min-height: 0;
  overflow: hidden;
}

.artifact-preview-content {
  min-height: 0;
  overflow: auto;
  padding-right: 4px;
}

.artifact-meta,
.muted {
  color: var(--text-secondary);
}

.artifact-preview-meta strong,
.artifact-preview-name {
  min-width: 0;
  overflow-wrap: anywhere;
}

.artifact-preview-name {
  margin: 0;
}

.secondary-button {
  min-height: 38px;
  padding: 0 14px;
  border-radius: 8px;
  font: inherit;
  border: 1px solid var(--border-default);
  background: var(--surface-default);
  color: var(--text-primary);
}

.preview-image {
  display: block;
  max-width: 100%;
  border-radius: 8px;
}

.artifact-preview-image-frame {
  min-height: 0;
  height: 100%;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid var(--border-default);
  background: var(--surface-subtle);
}

.artifact-preview-image {
  width: 100%;
  height: 100%;
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  object-position: center;
}

.icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  padding: 0;
}

.artifact-info-popover {
  position: relative;
}

.artifact-info-card,
.artifact-info-section,
.artifact-info-list {
  display: grid;
  gap: 10px;
  min-width: 0;
}

.artifact-info-card {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  z-index: 2;
  width: min(360px, calc(100vw - 48px));
  padding: 12px;
  border-radius: 12px;
  border: 1px solid var(--border-default);
  background: var(--surface-default);
  box-shadow: 0 16px 36px color-mix(in srgb, black 14%, transparent);
}

.artifact-info-list {
  grid-template-columns: minmax(84px, auto) minmax(0, 1fr);
  gap: 6px 10px;
}

.artifact-info-list dt {
  color: var(--text-secondary);
}

.artifact-info-list dd {
  margin: 0;
  overflow-wrap: anywhere;
}

pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
  overflow-x: auto;
  max-width: 100%;
}

@media (max-width: 880px) {
  .artifact-preview-modal {
    padding: 12px;
  }

  .artifact-preview-card {
    height: 92vh;
    padding: 16px;
  }

  .artifact-preview-header {
    grid-template-columns: 1fr;
  }

  .artifact-preview-header-actions {
    justify-content: space-between;
  }

  .artifact-info-card {
    width: min(100vw - 24px, 100%);
    right: 0;
  }
}
</style>
