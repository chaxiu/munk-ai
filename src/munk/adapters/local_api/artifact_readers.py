from __future__ import annotations

import mimetypes
import re
from pathlib import Path
from typing import Callable, cast

from munk.adapters.local_api.response_models import (
    CaseRunArtifactSummaryData,
    OperationArtifactsData,
    RunArtifactChildItemData,
    RunArtifactChildrenData,
    RunArtifactContentData,
    RunArtifactGroupData,
    RunArtifactItemData,
)
from munk.adapters.shared.payload_models import AttemptTokenUsageData, TokenUsageData
from munk.services.artifact_manifest_models import ArtifactManifest, ArtifactRef
from munk.services.artifact_manifest_service import ArtifactManifestService
from munk.services.operations.models import OperationRecord
from munk.services.operations.payloads import (
    infer_phase,
    infer_platform,
    infer_run_type,
    infer_target_label,
    infer_title,
    token_usage_from_result_json,
)


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


def build_operation_artifacts_data(
    record: OperationRecord,
    *,
    manifest_service: ArtifactManifestService,
    content_url_for: Callable[[str], str],
    download_url_for: Callable[[str], str],
    artifact_summary: dict[str, object],
) -> OperationArtifactsData:
    case_usage_by_case_id = _case_token_usage_by_case_id(record)
    primary_artifact_ids = cast(list[str], artifact_summary.get("primary_artifact_ids") or [])
    schema_versions = cast(dict[str, str], artifact_summary.get("schema_versions") or {})
    warning_summary = cast(list[str], artifact_summary.get("warning_summary") or [])
    try:
        manifest = _load_manifest(record, manifest_service=manifest_service)
    except ArtifactManifestNotFoundError:
        return _fallback_operation_artifacts_data(
            record,
            primary_artifact_ids=primary_artifact_ids,
            schema_versions=schema_versions,
            warning_summary=warning_summary,
            artifact_summary=artifact_summary,
            content_url_for=content_url_for,
            download_url_for=download_url_for,
        )
    primary_artifacts = _dedupe_artifact_items(
        [
        _artifact_item(
            ref,
            label=ref.role,
            content_url_for=content_url_for,
            download_url_for=download_url_for,
        )
        for ref in manifest.primary_artifacts.values()
        ]
    )
    artifact_groups: list[RunArtifactGroupData] = []
    seen_artifact_keys: set[tuple[str, str]] = set()
    if primary_artifacts:
        group_items = _dedupe_artifact_items(primary_artifacts, seen_keys=seen_artifact_keys)
        artifact_groups.append(
            RunArtifactGroupData(
                group_id="primary",
                title="Primary Artifacts",
                items=group_items,
            )
        )
    for case_run in manifest.case_runs:
        items = _dedupe_artifact_items(
            [
            _artifact_item(
                ref,
                label=f"{case_run.case_id} / {ref.role}",
                case_id=case_run.case_id,
                content_url_for=content_url_for,
                download_url_for=download_url_for,
            )
            for ref in case_run.artifacts.values()
            ]
        )
        group_items = _dedupe_artifact_items(items, seen_keys=seen_artifact_keys)
        if not group_items:
            continue
        artifact_groups.append(
            RunArtifactGroupData(
                group_id=f"case:{case_run.case_id}",
                title=case_run.title,
                items=group_items,
            )
        )
    return OperationArtifactsData(
        operation_id=record.operation_id,
        run_type=infer_run_type(record),
        title=infer_title(record),
        platform=infer_platform(record),
        phase=infer_phase(record),
        target_label=infer_target_label(record),
        source_recording_id=_source_recording_id(record),
        status=record.status,
        verification_verdict=record.verification_verdict,
        device_ref=record.device_ref,
        resource_scope=record.resource_scope,
        conflict_reason=record.conflict_reason,
        artifact_manifest_path=str(_manifest_path(record)),
        repro_dir=record.artifacts_json.get("repro_dir"),
        primary_artifact_ids=primary_artifact_ids,
        artifact_manifest_version=cast(int | None, artifact_summary.get("artifact_manifest_version")),
        schema_versions=schema_versions,
        diagnostics_path=cast(str | None, artifact_summary.get("diagnostics_path")),
        duration_ms=cast(int | None, artifact_summary.get("duration_ms")),
        failure_category=cast(str | None, artifact_summary.get("failure_category")),
        warning_summary=warning_summary,
        case_runs=[_build_case_run_artifact_summary(case_run, case_usage_by_case_id) for case_run in manifest.case_runs],
        reproduction_entries=list(manifest.reproduction),
        upstream_review=manifest.upstream_review,
        metadata=dict(manifest.metadata),
        primary_artifacts=primary_artifacts,
        artifact_groups=artifact_groups,
        token_usage=_usage_data_from_payload(artifact_summary.get("token_usage")),
        planning_usage=_usage_data_from_payload(artifact_summary.get("planning_usage")),
        execution_usage=_usage_data_from_payload(artifact_summary.get("execution_usage")),
        attempt_usages=_attempt_usage_data_list(artifact_summary.get("attempt_usages")),
    )


def resolve_artifact_content(
    record: OperationRecord,
    *,
    artifact_id: str,
    manifest_service: ArtifactManifestService,
    max_bytes: int,
) -> RunArtifactContentData:
    ref = resolve_artifact_ref(record, artifact_id=artifact_id, manifest_service=manifest_service)
    media_type = ref.media_type or "application/octet-stream"
    if not _is_preview_supported(ref):
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


def resolve_artifact_ref(
    record: OperationRecord,
    *,
    artifact_id: str,
    manifest_service: ArtifactManifestService,
) -> ArtifactRef:
    manifest = _load_manifest(record, manifest_service=manifest_service)
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


def _load_manifest(
    record: OperationRecord,
    *,
    manifest_service: ArtifactManifestService,
) -> ArtifactManifest:
    manifest_path = _manifest_path(record)
    if not manifest_path.exists():
        raise ArtifactManifestNotFoundError(f"artifact manifest missing: {manifest_path}")
    return manifest_service.load_manifest(manifest_path)


def _manifest_path(record: OperationRecord) -> Path:
    raw = record.artifacts_json.get("artifact_manifest")
    if not raw:
        raise ArtifactManifestNotFoundError("artifact manifest missing")
    return Path(raw)


def _artifact_item(
    ref: ArtifactRef,
    *,
    label: str,
    content_url_for: Callable[[str], str],
    download_url_for: Callable[[str], str],
    case_id: str | None = None,
) -> RunArtifactItemData:
    preview_supported = _is_preview_supported(ref)
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


def _dedupe_artifact_items(
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


def _fallback_operation_artifacts_data(
    record: OperationRecord,
    *,
    primary_artifact_ids: list[str],
    schema_versions: dict[str, str],
    warning_summary: list[str],
    artifact_summary: dict[str, object],
    content_url_for: Callable[[str], str],
    download_url_for: Callable[[str], str],
) -> OperationArtifactsData:
    primary_artifacts = [
        _artifact_item_from_path(
            artifact_id=artifact_id,
            path=Path(raw_path),
            content_url_for=content_url_for,
            download_url_for=download_url_for,
        )
        for artifact_id in primary_artifact_ids
        for raw_path in [record.artifacts_json.get(artifact_id)]
        if isinstance(raw_path, str) and raw_path
    ]
    artifact_groups = [
        RunArtifactGroupData(
            group_id="primary",
            title="Primary Artifacts",
            items=primary_artifacts,
        )
    ] if primary_artifacts else []
    return OperationArtifactsData(
        operation_id=record.operation_id,
        run_type=infer_run_type(record),
        title=infer_title(record),
        platform=infer_platform(record),
        phase=infer_phase(record),
        target_label=infer_target_label(record),
        source_recording_id=_source_recording_id(record),
        status=record.status,
        verification_verdict=record.verification_verdict,
        device_ref=record.device_ref,
        resource_scope=record.resource_scope,
        conflict_reason=record.conflict_reason,
        artifact_manifest_path=cast(str | None, artifact_summary.get("artifact_manifest_path")),
        repro_dir=record.artifacts_json.get("repro_dir"),
        primary_artifact_ids=primary_artifact_ids,
        artifact_manifest_version=cast(int | None, artifact_summary.get("artifact_manifest_version")),
        schema_versions=schema_versions,
        diagnostics_path=cast(str | None, artifact_summary.get("diagnostics_path")),
        duration_ms=cast(int | None, artifact_summary.get("duration_ms")),
        failure_category=cast(str | None, artifact_summary.get("failure_category")),
        warning_summary=warning_summary,
        case_runs=[],
        reproduction_entries=[],
        upstream_review=None,
        metadata={},
        primary_artifacts=primary_artifacts,
        artifact_groups=artifact_groups,
        token_usage=_usage_data_from_payload(artifact_summary.get("token_usage")),
        planning_usage=_usage_data_from_payload(artifact_summary.get("planning_usage")),
        execution_usage=_usage_data_from_payload(artifact_summary.get("execution_usage")),
        attempt_usages=_attempt_usage_data_list(artifact_summary.get("attempt_usages")),
    )


def _artifact_item_from_path(
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
    preview_supported = exists and not is_dir and _is_media_type_preview_supported(media_type)
    download_supported = exists and not is_dir
    return RunArtifactItemData(
        artifact_id=artifact_id,
        role=artifact_id,
        kind=kind,
        scope="operation",
        media_type=media_type,
        exists=exists,
        label=artifact_id,
        case_id=None,
        path=str(path),
        metadata={},
        content_url=content_url_for(artifact_id) if preview_supported else None,
        download_url=download_url_for(artifact_id) if download_supported else None,
    )


def _is_preview_supported(ref: ArtifactRef) -> bool:
    if not ref.exists or ref.path.is_dir():
        return False
    return _is_media_type_preview_supported(ref.media_type)


def _is_media_type_preview_supported(media_type: str | None) -> bool:
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
            if child.is_file() and _is_supported_image_path(child)
        ),
        key=_natural_sort_key,
    )


def _is_supported_image_path(path: Path) -> bool:
    suffix = path.suffix.lower()
    return suffix in {".png", ".jpg", ".jpeg", ".webp"}


def _natural_sort_key(path: Path) -> list[object]:
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", path.name)
        if part
    ]


def _source_recording_id(record: OperationRecord) -> str | None:
    for source in (record.request_json, record.result_json, record.progress_json):
        if isinstance(source, dict):
            candidate = source.get("recording_id")
            if isinstance(candidate, str) and candidate.strip():
                return candidate
    return None


def _case_token_usage_by_case_id(record: OperationRecord) -> dict[str, TokenUsageData]:
    if not isinstance(record.result_json, dict):
        return {}
    raw_items = record.result_json.get("items")
    if not isinstance(raw_items, list):
        return {}
    payload: dict[str, TokenUsageData] = {}
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        case_id = item.get("case_id")
        token_usage = token_usage_from_result_json(item)
        if isinstance(case_id, str) and case_id and token_usage is not None:
            usage = _usage_data_from_payload(token_usage)
            if usage is not None:
                payload[case_id] = usage
    return payload


def _build_case_run_artifact_summary(
    case_run,
    case_usage_by_case_id: dict[str, TokenUsageData],
) -> CaseRunArtifactSummaryData:
    token_usage: TokenUsageData | None = case_usage_by_case_id.get(case_run.case_id)
    return CaseRunArtifactSummaryData(
        case_id=case_run.case_id,
        title=case_run.title,
        operation_id=case_run.operation_id,
        verdict=case_run.verdict,
        execution_status=case_run.execution_status,
        run_dir=str(case_run.run_dir),
        token_usage=token_usage,
    )


def _usage_data_from_payload(payload: object) -> TokenUsageData | None:
    if not isinstance(payload, dict):
        return None
    try:
        return TokenUsageData.model_validate(payload)
    except Exception:
        return None


def _attempt_usage_data_list(payload: object) -> list[AttemptTokenUsageData]:
    if not isinstance(payload, list):
        return []
    items: list[AttemptTokenUsageData] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        try:
            items.append(AttemptTokenUsageData.model_validate(item))
        except Exception:
            continue
    return items
