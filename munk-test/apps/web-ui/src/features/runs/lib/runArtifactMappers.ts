import type { OperationArtifactsData, RunArtifactItemData } from '@/shared/api/operations'

export function isImageArtifact(item: Pick<RunArtifactItemData, 'media_type'>): boolean {
  return Boolean(item.media_type?.startsWith('image/'))
}

export function isDirectoryArtifact(item: Pick<RunArtifactItemData, 'kind'>): boolean {
  return item.kind === 'directory' || item.kind === 'image_directory'
}

export function isScreenshotDirectoryArtifact(item: Pick<RunArtifactItemData, 'kind'>): boolean {
  return item.kind === 'image_directory'
}

export function canPreviewArtifact(item: Pick<RunArtifactItemData, 'content_url'>): boolean {
  return Boolean(item.content_url)
}

export function canInteractArtifact(item: Pick<RunArtifactItemData, 'kind' | 'content_url' | 'download_url'>): boolean {
  return !isDirectoryArtifact(item) && Boolean(item.content_url || item.download_url)
}

export function flattenArtifacts(data?: OperationArtifactsData | null): RunArtifactItemData[] {
  if (!data) {
    return []
  }
  return (data.artifact_groups ?? []).flatMap((group) => group.items ?? [])
}

export function pickPrimaryArtifacts(data?: OperationArtifactsData | null): RunArtifactItemData[] {
  if (!data) {
    return []
  }
  const primaryIds = new Set(data.primary_artifact_ids ?? [])
  const flat = flattenArtifacts(data)
  const preferred = flat.filter((item) => primaryIds.has(item.artifact_id))
  if (preferred.length > 0) {
    return preferred
  }
  return data.primary_artifacts ?? []
}

export function findArtifactByPath(
  data: OperationArtifactsData | null | undefined,
  path: string | null | undefined,
): RunArtifactItemData | null {
  if (!data || !path) {
    return null
  }
  return flattenArtifacts(data).find((item) => item.path === path) ?? null
}
