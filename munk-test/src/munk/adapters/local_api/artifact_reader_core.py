from __future__ import annotations

import mimetypes
import re
from pathlib import Path
from typing import Callable, cast

from munk.adapters.local_api.response_models import RunArtifactItemData
from munk.artifacts import ARTIFACT_ID_ARTIFACT_MANIFEST, artifact_label
from munk.services.artifact_manifest_models import ArtifactManifest, ArtifactRef, ArtifactSchemaVersions
from munk.services.artifact_manifest_service import ArtifactManifestService
from munk.services.operations.models import OperationRecord
from munk.services.operations.payloads import source_recording_id


class ArtifactReadError(RuntimeError):
    code = "artifact_read_failed"


class ArtifactManifestNotFoundError(ArtifactReadError):
    code = "artifact_manifest_not_found"


class ArtifactNotFoundError(ArtifactReadError):
    code = "artifact_not_found"


class ArtifactPreviewUnsupportedError(ArtifactReadError):
    code = "artifact_preview_unsupported"


class ArtifactChildrenUnsupportedError(ArtifactReadError):
    code = "artifact_children_unsupported"


def schema_versions_from_summary(value: object) -> ArtifactSchemaVersions:
    if isinstance(value, ArtifactSchemaVersions):
        return value
    if isinstance(value, dict):
        return ArtifactSchemaVersions.from_mapping(cast(dict[str, str], value))
    return ArtifactSchemaVersions()


def load_manifest(
    record: OperationRecord,
    *,
    manifest_service: ArtifactManifestService,
) -> ArtifactManifest:
    manifest_path = get_manifest_path(record)
    if not manifest_path.exists():
        raise ArtifactManifestNotFoundError(f"artifact manifest missing: {manifest_path}")
    return manifest_service.load_manifest(manifest_path)


def get_manifest_path(record: OperationRecord) -> Path:
    raw = record.artifacts_json.get(ARTIFACT_ID_ARTIFACT_MANIFEST)
    if not raw:
        raise ArtifactManifestNotFoundError("artifact manifest missing")
    return Path(raw)


def resolve_artifact_ref(
    record: OperationRecord,
    *,
    artifact_id: str,
    manifest_service: ArtifactManifestService,
) -> ArtifactRef:
    manifest = load_manifest(record, manifest_service=manifest_service)
    if artifact_id in manifest.primary_artifacts:
        return manifest.primary_artifacts[artifact_id]
    for case_run in manifest.case_runs:
        if artifact_id in case_run.artifacts:
            return case_run.artifacts[artifact_id]
    raise ArtifactNotFoundError(f"artifact not found: {artifact_id}")


def resolve_image_directory_ref(
    record: OperationRecord,
    *,
    artifact_id: str,
    manifest_service: ArtifactManifestService,
) -> ArtifactRef:
    ref = resolve_artifact_ref(record, artifact_id=artifact_id, manifest_service=manifest_service)
    if ref.kind != "image_directory":
        raise ArtifactChildrenUnsupportedError(f"artifact children unsupported: {artifact_id}")
    if not ref.exists or not ref.path.is_dir():
        raise ArtifactNotFoundError(f"artifact not found: {artifact_id}")
    return ref


def artifact_item(
    ref: ArtifactRef,
    *,
    label: str,
    content_url_for: Callable[[str], str],
    download_url_for: Callable[[str], str],
    case_id: str | None = None,
) -> RunArtifactItemData:
    preview_supported = is_preview_supported(ref)
    downloadable = ref.exists and not ref.path.is_dir()
    return RunArtifactItemData(
        artifact_id=ref.artifact_id,
        role=ref.role,
        kind=ref.kind,
        scope=ref.scope,
        media_type=ref.media_type,
        exists=ref.exists,
        label=label,
        case_id=case_id,
        path=str(ref.path),
        metadata=dict(ref.metadata),
        content_url=content_url_for(ref.artifact_id) if preview_supported and ref.exists else None,
        download_url=download_url_for(ref.artifact_id) if downloadable else None,
    )


def artifact_item_from_path(
    *,
    artifact_id: str,
    path: Path,
    content_url_for: Callable[[str], str],
    download_url_for: Callable[[str], str],
) -> RunArtifactItemData:
    exists = path.exists()
    is_dir = exists and path.is_dir()
    media_type = None if is_dir else mimetypes.guess_type(str(path))[0]
    kind = "directory" if is_dir else "file"
    preview_supported = exists and not is_dir and is_media_type_preview_supported(media_type)
    download_supported = exists and not is_dir
    return RunArtifactItemData(
        artifact_id=artifact_id,
        role=artifact_id,
        kind=kind,
        scope="operation",
        media_type=media_type,
        exists=exists,
        label=artifact_label(artifact_id),
        case_id=None,
        path=str(path),
        metadata={},
        content_url=content_url_for(artifact_id) if preview_supported else None,
        download_url=download_url_for(artifact_id) if download_supported else None,
    )


def dedupe_artifact_items(
    items: list[RunArtifactItemData],
    *,
    seen_keys: set[tuple[str, str]] | None = None,
) -> list[RunArtifactItemData]:
    unique_items: list[RunArtifactItemData] = []
    known_keys: set[tuple[str, str]] = seen_keys if seen_keys is not None else set()
    for item in items:
        key = (item.kind, item.path)
        if key in known_keys:
            continue
        known_keys.add(key)
        unique_items.append(item)
    return unique_items


def is_preview_supported(ref: ArtifactRef) -> bool:
    if not ref.exists or ref.path.is_dir():
        return False
    return is_media_type_preview_supported(ref.media_type)


def is_media_type_preview_supported(media_type: str | None) -> bool:
    normalized = media_type or ""
    return normalized.startswith("text/") or normalized in {
        "application/json",
        "application/xml",
        "application/x-ndjson",
    }


def iter_image_directory_children(ref: ArtifactRef) -> list[Path]:
    return sorted(
        (
            child
            for child in ref.path.iterdir()
            if child.is_file() and is_supported_image_path(child)
        ),
        key=natural_sort_key,
    )


def is_supported_image_path(path: Path) -> bool:
    suffix = path.suffix.lower()
    return suffix in {".png", ".jpg", ".jpeg", ".webp"}


def natural_sort_key(path: Path) -> list[object]:
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", path.name)
        if part
    ]


def resolve_source_recording_id(record: OperationRecord) -> str | None:
    return source_recording_id(record)
