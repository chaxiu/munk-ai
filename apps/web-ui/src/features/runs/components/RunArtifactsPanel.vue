<script setup lang="ts">
import { Info } from '@lucide/vue'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import AppEmptyState from '@/shared/components/AppEmptyState.vue'
import { LocalApiClientError } from '@/shared/api/client'
import type { OperationArtifactsData } from '@/shared/api/operations'
import { translateErrorCode } from '@/shared/i18n/errorMessages'
import { isScreenshotDirectoryArtifact, flattenArtifacts } from '@/features/runs/lib/runMappers'
import { useRunArtifactChildrenQuery } from '@/features/runs/queries/useRunArtifactChildrenQuery'

type CaseRunWithOperation = {
  case_id: string
  title: string
  verdict: string
  execution_status: string
  run_dir: string
  operation_id?: string | null
}

type ArtifactInfoEntry = {
  label: string
  value: string
}

const props = defineProps<{
  operationId: string
  artifacts: OperationArtifactsData | null | undefined
}>()
defineEmits<{
  (event: 'preview-artifact', artifactId: string): void
}>()

const { t } = useI18n()

const selectedScreenshotArtifactId = ref<string | null>(null)
const selectedScreenshotChildId = ref<string | null>(null)
const isScreenshotInfoOpen = ref(false)

const allArtifacts = computed(() => flattenArtifacts(props.artifacts))
const caseRuns = computed<CaseRunWithOperation[]>(() => (props.artifacts?.case_runs ?? []) as CaseRunWithOperation[])
const selectedScreenshotArtifact = computed(() => {
  if (!selectedScreenshotArtifactId.value) {
    return null
  }
  return allArtifacts.value.find((item) => (
    item.artifact_id === selectedScreenshotArtifactId.value && isScreenshotDirectoryArtifact(item)
  )) ?? null
})

const screenshotChildrenQuery = useRunArtifactChildrenQuery(
  computed(() => props.operationId),
  selectedScreenshotArtifactId,
)

const screenshotChildren = computed(() => screenshotChildrenQuery.data.value?.items ?? [])
const selectedScreenshotChild = computed(() => {
  if (selectedScreenshotChildId.value) {
    return screenshotChildren.value.find((item) => item.child_id === selectedScreenshotChildId.value) ?? null
  }
  return screenshotChildren.value[0] ?? null
})

const screenshotBrowserError = computed(() => {
  const error = screenshotChildrenQuery.error.value
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

function buildArtifactInfoEntries(entries: Array<{ label: string, value: string | null | undefined }>): ArtifactInfoEntry[] {
  return entries.flatMap((entry) => {
    const value = entry.value?.trim()
    return value ? [{ label: entry.label, value }] : []
  })
}

const screenshotArtifactInfo = computed<ArtifactInfoEntry[]>(() => {
  const artifact = selectedScreenshotArtifact.value
  if (!artifact) {
    return []
  }
  return buildArtifactInfoEntries([
    { label: t('artifactPreview.fields.name'), value: artifact.label },
    { label: t('artifactPreview.fields.kind'), value: artifact.kind },
    { label: t('artifactPreview.fields.role'), value: artifact.role },
    { label: t('artifactPreview.fields.scope'), value: artifact.scope },
    { label: t('artifactPreview.fields.mediaType'), value: artifact.media_type ?? null },
    { label: t('artifactPreview.fields.path'), value: artifact.path },
  ])
})

const screenshotChildInfo = computed<ArtifactInfoEntry[]>(() => {
  const child = selectedScreenshotChild.value
  if (!child) {
    return []
  }
  return buildArtifactInfoEntries([
    { label: t('artifactPreview.fields.name'), value: child.name },
    { label: t('artifactPreview.fields.mediaType'), value: child.media_type ?? null },
    { label: t('artifactPreview.fields.path'), value: child.path },
  ])
})

watch([selectedScreenshotArtifact, screenshotChildren], ([artifact, items]) => {
  if (!artifact) {
    selectedScreenshotChildId.value = null
    return
  }
  if (selectedScreenshotChildId.value && items.some((item) => item.child_id === selectedScreenshotChildId.value)) {
    return
  }
  selectedScreenshotChildId.value = items[0]?.child_id ?? null
}, { immediate: true })

function closeScreenshotBrowser() {
  selectedScreenshotArtifactId.value = null
  selectedScreenshotChildId.value = null
  isScreenshotInfoOpen.value = false
}

function openScreenshotBrowser(artifactId: string) {
  selectedScreenshotArtifactId.value = artifactId
  selectedScreenshotChildId.value = null
  isScreenshotInfoOpen.value = false
}

function handleWindowKeydown(event: KeyboardEvent) {
  if (event.key !== 'Escape' || !selectedScreenshotArtifactId.value) {
    return
  }
  event.preventDefault()
  closeScreenshotBrowser()
}

onMounted(() => {
  window.addEventListener('keydown', handleWindowKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleWindowKeydown)
})
</script>

<template>
  <AppEmptyState
    v-if="(artifacts?.artifact_groups ?? []).length === 0"
    :title="t('runDetail.artifacts.emptyTitle')"
    :description="t('runDetail.artifacts.emptyDescription')"
  />
  <div v-else class="artifact-groups">
    <div class="panel-grid">
      <div class="meta-item"><span class="meta-label">{{ t('runDetail.fields.artifactManifestPath') }}</span><strong class="value-text">{{ artifacts?.artifact_manifest_path || '-' }}</strong></div>
      <div class="meta-item"><span class="meta-label">{{ t('runDetail.fields.reproDir') }}</span><strong class="value-text">{{ artifacts?.repro_dir || '-' }}</strong></div>
      <div class="meta-item full"><span class="meta-label">{{ t('runDetail.fields.schemaVersions') }}</span><pre class="json-block">{{ JSON.stringify(artifacts?.schema_versions ?? {}, null, 2) }}</pre></div>
      <div class="meta-item full"><span class="meta-label">{{ t('runDetail.fields.manifestMetadata') }}</span><pre class="json-block">{{ JSON.stringify(artifacts?.metadata ?? {}, null, 2) }}</pre></div>
      <div class="meta-item full" v-if="(artifacts?.reproduction_entries ?? []).length > 0">
        <span class="meta-label">{{ t('runDetail.fields.reproductionEntries') }}</span>
        <pre class="json-block">{{ JSON.stringify(artifacts?.reproduction_entries ?? [], null, 2) }}</pre>
      </div>
      <div class="meta-item full" v-if="artifacts?.upstream_review">
        <span class="meta-label">{{ t('runDetail.fields.upstreamReview') }}</span>
        <pre class="json-block">{{ JSON.stringify(artifacts.upstream_review, null, 2) }}</pre>
      </div>
    </div>
    <div v-if="caseRuns.length > 0" class="artifact-group">
      <h3>{{ t('runDetail.artifacts.caseRunsTitle') }}</h3>
      <article v-for="caseRun in caseRuns" :key="caseRun.case_id" class="artifact-row">
        <div class="artifact-main">
          <strong>{{ caseRun.title }}</strong>
          <div class="artifact-meta">
            <span>{{ caseRun.case_id }}</span>
            <span v-if="caseRun.operation_id">{{ caseRun.operation_id }}</span>
            <span>{{ caseRun.verdict }}</span>
            <span>{{ caseRun.execution_status }}</span>
            <span>{{ caseRun.run_dir }}</span>
          </div>
        </div>
        <div v-if="caseRun.operation_id" class="artifact-actions">
          <a class="secondary-link" :href="`/runs/${encodeURIComponent(caseRun.operation_id)}`">
            {{ t('runDetail.batch.openChild') }}
          </a>
        </div>
      </article>
    </div>
    <div v-for="group in artifacts?.artifact_groups ?? []" :key="group.group_id" class="artifact-group">
      <h3>{{ group.title }}</h3>
      <article v-for="item in group.items ?? []" :key="item.artifact_id" class="artifact-row">
        <div class="artifact-main">
          <strong>{{ item.label }}</strong>
          <div class="artifact-meta">
            <span>{{ item.kind }}</span>
            <span>{{ item.role }}</span>
            <span>{{ item.scope }}</span>
            <span>{{ item.exists ? t('runDetail.artifacts.exists') : t('runDetail.artifacts.missing') }}</span>
            <span>{{ item.media_type || '-' }}</span>
            <span>{{ item.path }}</span>
          </div>
        </div>
        <div class="artifact-actions">
          <button
            v-if="isScreenshotDirectoryArtifact(item)"
            type="button"
            class="secondary-button"
            :class="{ active: selectedScreenshotArtifactId === item.artifact_id }"
            :aria-pressed="selectedScreenshotArtifactId === item.artifact_id"
            @click="openScreenshotBrowser(item.artifact_id)"
          >
            {{ t('runDetail.actions.viewScreenshots') }}
          </button>
          <button
            v-else-if="item.content_url || item.download_url"
            type="button"
            class="secondary-button"
            @click="$emit('preview-artifact', item.artifact_id)"
          >
            {{ t('runDetail.actions.preview') }}
          </button>
          <a v-if="item.download_url" class="secondary-link" :href="item.download_url" target="_blank" rel="noreferrer">
            {{ t('runDetail.actions.download') }}
          </a>
        </div>
      </article>
    </div>
  </div>
  <Teleport to="body">
    <div
      v-if="selectedScreenshotArtifact"
      class="screenshot-modal"
      data-testid="screenshot-modal"
      role="dialog"
      aria-modal="true"
      :aria-label="t('runDetail.artifacts.screenshotDialogTitle')"
    >
      <button
        type="button"
        class="screenshot-modal-backdrop"
        data-testid="screenshot-modal-backdrop"
        :aria-label="t('runDetail.actions.closeScreenshots')"
        @click="closeScreenshotBrowser"
      />
      <div class="screenshot-modal-card">
        <div class="screenshot-modal-header">
          <div class="artifact-main">
            <strong>{{ t('runDetail.artifacts.screenshotDialogTitle') }}</strong>
            <p v-if="selectedScreenshotChild" class="muted screenshot-current-name">
              {{ selectedScreenshotChild.name }}
            </p>
          </div>
          <div class="screenshot-modal-header-actions">
            <div v-if="screenshotArtifactInfo.length > 0 || screenshotChildInfo.length > 0" class="artifact-info-popover">
              <button
                type="button"
                class="secondary-button icon-button artifact-info-trigger"
                data-testid="screenshot-info-toggle"
                :aria-expanded="isScreenshotInfoOpen"
                :aria-label="t('artifactPreview.infoLabel')"
                :title="t('artifactPreview.infoLabel')"
                @click="isScreenshotInfoOpen = !isScreenshotInfoOpen"
              >
                <Info :size="16" aria-hidden="true" />
                <span class="sr-only">{{ t('artifactPreview.infoLabel') }}</span>
              </button>
              <div v-if="isScreenshotInfoOpen" class="artifact-info-card" data-testid="screenshot-info-panel">
                <div v-if="screenshotChildInfo.length > 0" class="artifact-info-section">
                  <strong>{{ t('artifactPreview.currentScreenshotTitle') }}</strong>
                  <dl class="artifact-info-list">
                    <template v-for="entry in screenshotChildInfo" :key="`child-${entry.label}`">
                      <dt>{{ entry.label }}</dt>
                      <dd>{{ entry.value }}</dd>
                    </template>
                  </dl>
                </div>
                <div v-if="screenshotArtifactInfo.length > 0" class="artifact-info-section">
                  <strong>{{ t('artifactPreview.sourceArtifactTitle') }}</strong>
                  <dl class="artifact-info-list">
                    <template v-for="entry in screenshotArtifactInfo" :key="`artifact-${entry.label}`">
                      <dt>{{ entry.label }}</dt>
                      <dd>{{ entry.value }}</dd>
                    </template>
                  </dl>
                </div>
              </div>
            </div>
            <button
              type="button"
              class="secondary-button screenshot-close-button"
              data-testid="screenshot-modal-close"
              @click="closeScreenshotBrowser"
            >
              {{ t('runDetail.actions.closeScreenshots') }}
            </button>
          </div>
        </div>
        <div class="screenshot-modal-body">
          <AppEmptyState
            v-if="screenshotBrowserError"
            :title="t('runDetail.artifacts.screenshotErrorTitle')"
            :description="screenshotBrowserError"
          />
          <AppEmptyState
            v-else-if="!screenshotChildrenQuery.isFetching.value && screenshotChildren.length === 0"
            :title="t('runDetail.artifacts.screenshotEmptyTitle')"
            :description="t('runDetail.artifacts.screenshotEmptyDescription')"
          />
          <p v-else-if="screenshotChildrenQuery.isFetching.value && screenshotChildren.length === 0" class="muted">
            {{ t('common.loading') }}
          </p>
          <div v-else class="screenshot-browser">
            <div class="screenshot-list">
              <button
                v-for="item in screenshotChildren"
                :key="item.child_id"
                type="button"
                class="screenshot-item"
                :class="{ active: selectedScreenshotChild?.child_id === item.child_id }"
                @click="selectedScreenshotChildId = item.child_id"
              >
                <strong>{{ item.name }}</strong>
              </button>
            </div>
            <div class="screenshot-panel">
              <div v-if="selectedScreenshotChild" class="screenshot-panel-header">
                <strong>{{ selectedScreenshotChild.name }}</strong>
              </div>
              <div class="screenshot-preview-frame">
                <img
                  v-if="selectedScreenshotChild?.content_url"
                  class="preview-image screenshot-preview"
                  :src="selectedScreenshotChild.content_url"
                  :alt="selectedScreenshotChild.name"
                >
                <p v-else class="muted">{{ t('artifactPreview.unsupported') }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.artifact-groups,
.artifact-group,
.screenshot-browser,
.screenshot-list,
.screenshot-panel {
  display: grid;
  gap: 12px;
  min-width: 0;
}

.panel-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  min-width: 0;
}

.meta-item {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.meta-item.full {
  grid-column: 1 / -1;
}

.meta-label,
.muted,
.artifact-meta {
  color: var(--text-secondary);
}

.json-block {
  margin: 0;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid var(--border-muted);
  background: var(--surface-subtle);
  min-width: 0;
  overflow-wrap: anywhere;
}

.artifact-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  padding-top: 12px;
  border-top: 1px solid var(--border-muted);
}

.artifact-main,
.artifact-actions,
.artifact-browser-header {
  display: grid;
  gap: 8px;
  min-width: 0;
}

.artifact-main {
  flex: 1 1 480px;
}

.artifact-actions {
  flex: 0 0 auto;
  align-content: start;
}

.artifact-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  font-size: 0.92rem;
  min-width: 0;
}

.artifact-meta > span,
.meta-item strong,
.artifact-main strong,
.value-text,
.screenshot-list,
.screenshot-panel {
  min-width: 0;
  overflow-wrap: anywhere;
}

.secondary-button,
.secondary-link {
  min-height: 38px;
  padding: 0 14px;
  border-radius: 8px;
  font: inherit;
  border: 1px solid var(--border-default);
  background: var(--surface-default);
  color: var(--text-primary);
}

.secondary-button.active {
  border-color: var(--accent-primary);
  color: var(--accent-primary);
}

.secondary-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.screenshot-modal {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.screenshot-modal-backdrop {
  position: absolute;
  inset: 0;
  border: 0;
  background: color-mix(in srgb, var(--surface-overlay) 70%, transparent);
}

.screenshot-modal-card,
.screenshot-modal-body,
.screenshot-modal-header {
  display: grid;
  gap: 12px;
  min-width: 0;
}

.screenshot-modal-card {
  position: relative;
  z-index: 1;
  width: min(1120px, 100%);
  height: min(88vh, 900px);
  padding: 20px;
  border-radius: 16px;
  border: 1px solid var(--border-default);
  background: var(--surface-default);
  box-shadow: 0 24px 60px color-mix(in srgb, black 20%, transparent);
  overflow: hidden;
  grid-template-rows: auto minmax(0, 1fr);
}

.screenshot-modal-header {
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: start;
}

.screenshot-modal-header-actions {
  position: relative;
  display: flex;
  align-items: start;
  gap: 8px;
}

.screenshot-modal-body {
  min-height: 0;
  overflow: hidden;
}

.screenshot-current-name,
.screenshot-panel-header {
  margin: 0;
}

.screenshot-close-button {
  align-self: start;
}

.screenshot-browser {
  grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
  align-items: stretch;
  min-height: 0;
  height: 100%;
}

.screenshot-list {
  min-height: 0;
  height: 100%;
  align-content: start;
  grid-auto-rows: max-content;
  overflow: auto;
  padding-right: 4px;
}

.screenshot-item {
  padding: 12px;
  border-radius: 8px;
  border: 1px solid var(--border-default);
  background: var(--surface-default);
  color: var(--text-primary);
  text-align: left;
}

.screenshot-item.active {
  border-color: var(--accent-primary);
}

.screenshot-panel {
  grid-template-rows: auto minmax(0, 1fr);
  height: 100%;
  overflow: hidden;
}

.screenshot-preview-frame {
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

.screenshot-preview {
  display: block;
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
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
  overflow-x: auto;
  max-width: 100%;
}

@media (max-width: 880px) {
  .panel-grid,
  .screenshot-browser {
    grid-template-columns: 1fr;
  }

  .screenshot-modal {
    padding: 12px;
  }

  .screenshot-modal-card {
    height: 92vh;
    padding: 16px;
  }

  .screenshot-modal-header {
    grid-template-columns: 1fr;
  }

  .screenshot-modal-header-actions {
    justify-content: space-between;
  }

  .artifact-info-card {
    width: min(100vw - 24px, 100%);
    right: 0;
  }
}
</style>
