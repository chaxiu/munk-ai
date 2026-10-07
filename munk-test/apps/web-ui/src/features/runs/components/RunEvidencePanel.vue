<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import AppEmptyState from '@/shared/components/AppEmptyState.vue'
import { LocalApiClientError } from '@/shared/api/client'
import { getOperationArtifactContent, type OperationArtifactsData, type OperationDetailData } from '@/shared/api/operations'
import { translateErrorCode } from '@/shared/i18n/errorMessages'
import {
  canInteractArtifact,
  canPreviewArtifact,
  findArtifactByPath,
  flattenArtifacts,
  isImageArtifact,
  pickPrimaryArtifacts,
  presentJudgeEvidenceItems,
} from '@/features/runs/lib/runMappers'

const props = defineProps<{
  operationId: string
  detail: OperationDetailData | null | undefined
  artifacts: OperationArtifactsData | null | undefined
  preferredEvidenceId?: string | null
}>()

const { t } = useI18n()

const selectedPreviewArtifactId = ref<string | null>(null)
const selectedEvidenceId = ref<string | null>(null)
const previewText = ref<string | null>(null)
const previewTextLoading = ref(false)
const previewTextMeta = ref<{ truncated: boolean, mediaType: string | null } | null>(null)

const allArtifacts = computed(() => flattenArtifacts(props.artifacts))
const primaryArtifacts = computed(() => pickPrimaryArtifacts(props.artifacts))
const judgeEvidence = computed(() => presentJudgeEvidenceItems(props.detail, t))
const previewableArtifacts = computed(() => allArtifacts.value.filter((item) => canInteractArtifact(item)))
const imageEvidence = computed(() => primaryArtifacts.value.find((item) => isImageArtifact(item)) ?? allArtifacts.value.find((item) => isImageArtifact(item)) ?? null)
const textEvidence = computed(() => primaryArtifacts.value.find((item) => canPreviewArtifact(item) && !isImageArtifact(item)) ?? allArtifacts.value.find((item) => canPreviewArtifact(item) && !isImageArtifact(item)) ?? null)
const selectedEvidence = computed(() => {
  if (selectedEvidenceId.value) {
    return judgeEvidence.value.find((item) => item.evidenceId === selectedEvidenceId.value) ?? null
  }
  return judgeEvidence.value[0] ?? null
})
const selectedPreviewArtifact = computed(() => {
  if (selectedPreviewArtifactId.value) {
    return allArtifacts.value.find((item) => item.artifact_id === selectedPreviewArtifactId.value) ?? null
  }
  const matchedArtifact = findArtifactByPath(props.artifacts, selectedEvidence.value?.path)
  if (matchedArtifact) {
    return matchedArtifact
  }
  return imageEvidence.value ?? textEvidence.value
})

watch(selectedPreviewArtifact, async (artifact) => {
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

watch(judgeEvidence, (items) => {
  if (selectedEvidenceId.value && items.every((item) => item.evidenceId !== selectedEvidenceId.value)) {
    selectedEvidenceId.value = items[0]?.evidenceId ?? null
  }
}, { immediate: true })

watch(
  [() => props.preferredEvidenceId, judgeEvidence],
  ([preferredEvidenceId, items]) => {
    if (!preferredEvidenceId) {
      return
    }
    const matched = items.find((item) => item.evidenceId === preferredEvidenceId)
    if (!matched) {
      return
    }
    selectedEvidenceId.value = matched.evidenceId
    selectedPreviewArtifactId.value = null
  },
  { immediate: true },
)
</script>

<template>
  <AppEmptyState
    v-if="!selectedEvidence && !selectedPreviewArtifact"
    :title="t('runDetail.evidence.emptyTitle')"
    :description="t('runDetail.evidence.emptyDescription')"
  />
  <div v-else class="evidence-layout">
    <div class="evidence-list">
      <template v-if="judgeEvidence.length > 0">
        <button
          v-for="item in judgeEvidence"
          :key="item.evidenceId"
          type="button"
          class="evidence-item"
          :class="{ active: selectedEvidence?.evidenceId === item.evidenceId }"
          @click="selectedEvidenceId = item.evidenceId; selectedPreviewArtifactId = null"
        >
          <strong>{{ item.title }}</strong>
          <p class="evidence-card-summary">{{ item.summary }}</p>
          <div class="artifact-meta">
            <span v-for="badge in item.badges" :key="badge">{{ badge }}</span>
          </div>
        </button>
      </template>
      <template v-else-if="previewableArtifacts.length > 0">
        <p class="muted">{{ t('runDetail.evidence.fallbackDescription') }}</p>
        <button
          v-for="item in previewableArtifacts"
          :key="item.artifact_id"
          type="button"
          class="evidence-item"
          :class="{ active: selectedPreviewArtifact?.artifact_id === item.artifact_id }"
          @click="selectedPreviewArtifactId = item.artifact_id"
        >
          <strong>{{ item.label }}</strong>
          <div class="artifact-meta">
            <span>{{ item.kind }}</span>
            <span>{{ item.role }}</span>
            <span>{{ item.media_type || '-' }}</span>
          </div>
          <span class="muted value-text">{{ item.path }}</span>
        </button>
      </template>
    </div>
    <div class="evidence-panel">
      <div v-if="selectedEvidence" class="evidence-summary">
        <div class="evidence-heading">
          <strong>{{ selectedEvidence.title }}</strong>
          <div class="artifact-meta">
            <span v-for="badge in selectedEvidence.badges" :key="badge">{{ badge }}</span>
          </div>
        </div>
        <p>{{ selectedEvidence.summary }}</p>
        <dl v-if="selectedEvidence.facts.length > 0" class="evidence-facts">
          <template v-for="fact in selectedEvidence.facts" :key="fact.label">
            <dt>{{ fact.label }}</dt>
            <dd>{{ fact.value }}</dd>
          </template>
        </dl>
        <details v-if="selectedEvidence.path || selectedEvidence.rawPayload" class="evidence-raw">
          <summary>{{ t('runDetail.evidence.rawTitle') }}</summary>
          <div class="evidence-raw-content">
            <p v-if="selectedEvidence.path" class="muted">{{ selectedEvidence.path }}</p>
            <pre v-if="selectedEvidence.rawPayload">{{ JSON.stringify(selectedEvidence.rawPayload, null, 2) }}</pre>
          </div>
        </details>
      </div>
      <p v-else-if="selectedPreviewArtifact" class="muted">{{ t('runDetail.evidence.fallbackHint') }}</p>
      <section v-if="selectedPreviewArtifact" class="preview-section">
        <div class="artifact-meta">
          <strong>{{ t('runDetail.evidence.previewTitle') }}</strong>
          <span>{{ selectedPreviewArtifact.label }}</span>
          <span>{{ selectedPreviewArtifact.media_type || '-' }}</span>
        </div>
      </section>
      <p v-else-if="selectedEvidence" class="muted">{{ t('runDetail.evidence.noArtifactMatch') }}</p>
      <p v-else class="muted">{{ t('runDetail.evidence.selectHint') }}</p>
      <img
        v-if="selectedPreviewArtifact && isImageArtifact(selectedPreviewArtifact) && selectedPreviewArtifact.download_url"
        class="preview-image"
        :src="selectedPreviewArtifact.download_url"
        :alt="selectedPreviewArtifact.label"
      >
      <template v-else-if="selectedPreviewArtifact">
        <p v-if="previewTextLoading" class="muted">{{ t('common.loading') }}</p>
        <p v-else-if="!selectedPreviewArtifact.content_url" class="muted">{{ t('artifactPreview.unsupported') }}</p>
        <div v-else>
          <p v-if="previewTextMeta?.truncated" class="muted">{{ t('artifactPreview.truncated') }}</p>
          <pre>{{ previewText }}</pre>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.evidence-layout,
.evidence-list,
.evidence-summary,
.evidence-item,
.evidence-panel {
  display: grid;
  gap: 12px;
  min-width: 0;
}

.evidence-layout {
  grid-template-columns: minmax(0, 320px) minmax(0, 1fr);
  align-items: start;
}

.evidence-card-summary {
  margin: 0;
  color: var(--text-secondary);
}

.evidence-item {
  padding: 12px;
  border-radius: 8px;
  border: 1px solid var(--border-default);
  background: var(--surface-default);
  color: var(--text-primary);
  text-align: left;
  overflow: hidden;
}

.evidence-item.active {
  border-color: var(--accent-primary);
}

.artifact-meta,
.muted {
  color: var(--text-secondary);
}

.artifact-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  font-size: 0.92rem;
  min-width: 0;
}

.evidence-heading {
  display: grid;
  gap: 6px;
}

.evidence-facts {
  display: grid;
  grid-template-columns: minmax(120px, auto) minmax(0, 1fr);
  gap: 8px 12px;
  margin: 0;
}

.evidence-facts dt {
  color: var(--text-secondary);
}

.evidence-facts dd {
  margin: 0;
}

.evidence-raw,
.preview-section {
  display: grid;
  gap: 8px;
  border-top: 1px solid var(--border-default);
  padding-top: 12px;
}

.evidence-raw summary {
  cursor: pointer;
  font-weight: 600;
}

.evidence-raw-content {
  display: grid;
  gap: 8px;
}

.artifact-meta > span,
.evidence-item strong,
.evidence-summary,
.evidence-panel,
.evidence-list,
.value-text {
  min-width: 0;
  overflow-wrap: anywhere;
}

.preview-image {
  max-width: 100%;
  border-radius: 8px;
  border: 1px solid var(--border-default);
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
  .evidence-layout {
    grid-template-columns: 1fr;
  }
}
</style>
