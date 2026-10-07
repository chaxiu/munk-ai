from __future__ import annotations

from pathlib import Path
from typing import Callable, cast

from munk.adapters.local_api.artifact_reader_core import (
    ArtifactManifestNotFoundError,
    artifact_item,
    artifact_item_from_path,
    dedupe_artifact_items,
    get_manifest_path,
    load_manifest,
    resolve_source_recording_id,
    schema_versions_from_summary,
)
from munk.adapters.local_api.artifact_reader_usage import (
    attempt_usage_data_list,
    build_case_run_artifact_summary,
    case_token_usage_by_case_id,
    usage_data_from_payload,
)
from munk.adapters.local_api.response_models import OperationArtifactsData, RunArtifactGroupData
from munk.services.artifact_manifest_models import ArtifactSchemaVersions
from munk.services.artifact_manifest_service import ArtifactManifestService
from munk.services.operations.models import OperationRecord
from munk.services.operations.payloads import (
    infer_phase,
    infer_platform,
    infer_run_type,
    infer_target_label,
    infer_title,
)


def build_operation_artifacts_data(
    record: OperationRecord,
    *,
    manifest_service: ArtifactManifestService,
    content_url_for: Callable[[str], str],
    download_url_for: Callable[[str], str],
    artifact_summary: dict[str, object],
) -> OperationArtifactsData:
    case_usage_by_case_id = case_token_usage_by_case_id(record)
    primary_artifact_ids = cast(list[str], artifact_summary.get("primary_artifact_ids") or [])
    schema_versions = schema_versions_from_summary(artifact_summary.get("schema_versions"))
    warning_summary = cast(list[str], artifact_summary.get("warning_summary") or [])
    try:
        manifest = load_manifest(record, manifest_service=manifest_service)
    except ArtifactManifestNotFoundError:
        return fallback_operation_artifacts_data(
            record,
            primary_artifact_ids=primary_artifact_ids,
            schema_versions=schema_versions,
            warning_summary=warning_summary,
            artifact_summary=artifact_summary,
            content_url_for=content_url_for,
            download_url_for=download_url_for,
        )

    primary_artifacts = dedupe_artifact_items(
        [
            artifact_item(
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
        artifact_groups.append(
            RunArtifactGroupData(
                group_id="primary",
                title="Primary Artifacts",
                items=dedupe_artifact_items(primary_artifacts, seen_keys=seen_artifact_keys),
            )
        )
    for case_run in manifest.case_runs:
        items = dedupe_artifact_items(
            [
                artifact_item(
                    ref,
                    label=f"{case_run.case_id} / {ref.role}",
                    case_id=case_run.case_id,
                    content_url_for=content_url_for,
                    download_url_for=download_url_for,
                )
                for ref in case_run.artifacts.values()
            ]
        )
        group_items = dedupe_artifact_items(items, seen_keys=seen_artifact_keys)
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
        source_recording_id=resolve_source_recording_id(record),
        status=record.status,
        verification_verdict=record.verification_verdict,
        device_ref=record.device_ref,
        resource_scope=record.resource_scope,
        conflict_reason=record.conflict_reason,
        artifact_manifest_path=str(get_manifest_path(record)),
        repro_dir=record.artifacts_json.get("repro_dir"),
        primary_artifact_ids=primary_artifact_ids,
        artifact_manifest_version=cast(int | None, artifact_summary.get("artifact_manifest_version")),
        schema_versions=schema_versions,
        diagnostics_path=cast(str | None, artifact_summary.get("diagnostics_path")),
        duration_ms=cast(int | None, artifact_summary.get("duration_ms")),
        failure_category=cast(str | None, artifact_summary.get("failure_category")),
        warning_summary=warning_summary,
        case_runs=[
            build_case_run_artifact_summary(case_run, case_usage_by_case_id)
            for case_run in manifest.case_runs
        ],
        reproduction_entries=list(manifest.reproduction),
        upstream_review=manifest.upstream_review,
        primary_artifacts=primary_artifacts,
        artifact_groups=artifact_groups,
        token_usage=usage_data_from_payload(artifact_summary.get("token_usage")),
        planning_usage=usage_data_from_payload(artifact_summary.get("planning_usage")),
        execution_usage=usage_data_from_payload(artifact_summary.get("execution_usage")),
        attempt_usages=attempt_usage_data_list(artifact_summary.get("attempt_usages")),
    )


def fallback_operation_artifacts_data(
    record: OperationRecord,
    *,
    primary_artifact_ids: list[str],
    schema_versions: ArtifactSchemaVersions,
    warning_summary: list[str],
    artifact_summary: dict[str, object],
    content_url_for: Callable[[str], str],
    download_url_for: Callable[[str], str],
) -> OperationArtifactsData:
    primary_artifacts = [
        artifact_item_from_path(
            artifact_id=artifact_id,
            path=Path(raw_path),
            content_url_for=content_url_for,
            download_url_for=download_url_for,
        )
        for artifact_id in primary_artifact_ids
        for raw_path in [record.artifacts_json.get(artifact_id)]
        if isinstance(raw_path, str) and raw_path
    ]
    artifact_groups = (
        [
            RunArtifactGroupData(
                group_id="primary",
                title="Primary Artifacts",
                items=primary_artifacts,
            )
        ]
        if primary_artifacts
        else []
    )
    return OperationArtifactsData(
        operation_id=record.operation_id,
        run_type=infer_run_type(record),
        title=infer_title(record),
        platform=infer_platform(record),
        phase=infer_phase(record),
        target_label=infer_target_label(record),
        source_recording_id=resolve_source_recording_id(record),
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
        primary_artifacts=primary_artifacts,
        artifact_groups=artifact_groups,
        token_usage=usage_data_from_payload(artifact_summary.get("token_usage")),
        planning_usage=usage_data_from_payload(artifact_summary.get("planning_usage")),
        execution_usage=usage_data_from_payload(artifact_summary.get("execution_usage")),
        attempt_usages=attempt_usage_data_list(artifact_summary.get("attempt_usages")),
    )
