from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Callable

from munk.adapters.local_api.artifact_reader_core import (
    ArtifactNotFoundError,
    ArtifactPreviewUnsupportedError,
    is_preview_supported,
    iter_image_directory_children,
    resolve_artifact_ref,
    resolve_image_directory_ref,
)
from munk.adapters.local_api.response_models import (
    RunArtifactChildItemData,
    RunArtifactChildrenData,
    RunArtifactContentData,
)
from munk.services.artifact_manifest_service import ArtifactManifestService
from munk.services.operations.models import OperationRecord


def resolve_artifact_content(
    record: OperationRecord,
    *,
    artifact_id: str,
    manifest_service: ArtifactManifestService,
    max_bytes: int,
) -> RunArtifactContentData:
    ref = resolve_artifact_ref(record, artifact_id=artifact_id, manifest_service=manifest_service)
    media_type = ref.media_type or "application/octet-stream"
    if not is_preview_supported(ref):
        raise ArtifactPreviewUnsupportedError(f"artifact preview unsupported: {artifact_id}")
    raw = ref.path.read_bytes()
    truncated = len(raw) > max_bytes
    payload = raw[:max_bytes]
    return RunArtifactContentData(
        artifact_id=artifact_id,
        media_type=media_type,
        encoding="utf-8",
        truncated=truncated,
        content=payload.decode("utf-8", errors="replace"),
    )


def list_artifact_children(
    record: OperationRecord,
    *,
    artifact_id: str,
    manifest_service: ArtifactManifestService,
    content_url_for: Callable[[str], str],
) -> RunArtifactChildrenData:
    ref = resolve_image_directory_ref(
        record,
        artifact_id=artifact_id,
        manifest_service=manifest_service,
    )
    items = [
        RunArtifactChildItemData(
            child_id=child_path.name,
            name=child_path.name,
            path=str(child_path),
            media_type=mimetypes.guess_type(str(child_path))[0],
            size_bytes=child_path.stat().st_size,
            content_url=content_url_for(child_path.name),
        )
        for child_path in iter_image_directory_children(ref)
    ]
    return RunArtifactChildrenData(
        operation_id=record.operation_id,
        artifact_id=artifact_id,
        title=ref.role,
        kind=ref.kind,
        items=items,
    )


def resolve_artifact_child_path(
    record: OperationRecord,
    *,
    artifact_id: str,
    child_id: str,
    manifest_service: ArtifactManifestService,
) -> Path:
    ref = resolve_image_directory_ref(
        record,
        artifact_id=artifact_id,
        manifest_service=manifest_service,
    )
    for child_path in iter_image_directory_children(ref):
        if child_path.name == child_id:
            return child_path
    raise ArtifactNotFoundError(f"artifact child not found: {artifact_id}/{child_id}")
