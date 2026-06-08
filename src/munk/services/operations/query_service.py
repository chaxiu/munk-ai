from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from munk.adapters.shared.payload_models import (
    BatchRunAggregateData,
    OperationChildItemData,
    OperationChildrenData,
    TokenUsageData,
)
from munk.services.artifact_manifest_service import ArtifactManifestService
from munk.services.diagnostics_service import OperationDiagnosticsService
from munk.services.machine_contracts import MachineCommandResponse, build_error_result, build_success_result
from munk.services.operations.models import OperationRecord
from munk.services.operations.payloads import (
    attempt_usages_from_result_json,
    build_operation_detail_payload,
    execution_usage_from_result_json,
    infer_run_type,
    infer_title,
    planning_usage_from_result_json,
    token_usage_from_result_json,
)
from munk.services.operations.service import OperationService
from munk.services.reproduction_service import ReproductionService
from munk.token_usage import TokenUsage, merge_token_usages


class OperationQueryService:
    def __init__(
        self,
        *,
        operation_service: OperationService,
        artifact_manifest_service: ArtifactManifestService | None = None,
        diagnostics_service: OperationDiagnosticsService | None = None,
        reproduction_service: ReproductionService | None = None,
    ) -> None:
        self._operation_service = operation_service
        self._artifact_manifest_service = artifact_manifest_service or ArtifactManifestService()
        self._diagnostics_service = diagnostics_service or OperationDiagnosticsService()
        self._reproduction_service = reproduction_service or ReproductionService(self._artifact_manifest_service)

    def get_operation(self, *, operation_id: str) -> MachineCommandResponse:
        try:
            record = self._operation_service.registry.get_operation(operation_id)
        except Exception as exc:
            return build_error_result(command="runs_get", exc=cast(Exception, exc))
        children = self._operation_service.registry.list_child_operations(operation_id)
        aggregate = self._build_batch_aggregate(children) if children else None
        children_preview = [self._build_child_item(record=item).model_dump(mode="json") for item in children]
        current_child_operation_id = aggregate.current_child_operation_id if aggregate is not None else None
        current_child_case_id = aggregate.current_child_case_id if aggregate is not None else None
        batch_kind = self._infer_batch_kind(record, children)
        data = build_operation_detail_payload(
            record,
            artifact_summary=self.artifact_summary(record),
            is_batch=bool(children),
            batch_kind=batch_kind,
            aggregate=aggregate.model_dump(mode="json") if aggregate is not None else None,
            current_child_operation_id=current_child_operation_id,
            current_child_case_id=current_child_case_id,
            children_preview=children_preview,
        )
        return build_success_result(
            command="runs_get",
            data=data,
            artifacts=record.artifacts_json,
        )

    def list_operation_events(
        self,
        *,
        operation_id: str,
        after_seq: int,
        limit: int,
    ) -> MachineCommandResponse:
        try:
            events = self._operation_service.registry.list_events(operation_id, after_seq=after_seq, limit=limit)
        except Exception as exc:
            return build_error_result(command="runs_events", exc=cast(Exception, exc))
        data: dict[str, Any] = {
            "operation_id": operation_id,
            "after_seq": after_seq,
            "limit": limit,
            "next_after_seq": events[-1].seq if events else after_seq,
            "items": [event.model_dump(mode="json") for event in events],
        }
        return build_success_result(command="runs_events", data=data)

    def get_operation_artifacts(self, *, operation_id: str) -> MachineCommandResponse:
        try:
            record = self._operation_service.registry.get_operation(operation_id)
        except Exception as exc:
            return build_error_result(command="runs_artifacts", exc=cast(Exception, exc))
        from munk.adapters.local_api.artifact_readers import build_operation_artifacts_data

        artifact_summary = self.artifact_summary(record)
        data = build_operation_artifacts_data(
            record,
            manifest_service=self._artifact_manifest_service,
            content_url_for=lambda artifact_id: (
                f"/v1/runs/{record.operation_id}/artifacts/{artifact_id}/content"
            ),
            download_url_for=lambda artifact_id: (
                f"/v1/runs/{record.operation_id}/artifacts/{artifact_id}/download"
            ),
            artifact_summary=artifact_summary,
        ).model_dump(mode="json")
        return build_success_result(
            command="runs_artifacts",
            data=data,
            artifacts=record.artifacts_json,
        )

    def cleanup_stale_claims(self) -> MachineCommandResponse:
        cleaned = self._operation_service.cleanup_stale_claims()
        return build_success_result(
            command="runs_cleanup_locks",
            data={
                "cleaned_count": len(cleaned),
                "items": [item.model_dump(mode="json") for item in cleaned],
            },
        )

    def cancel_operation(self, *, operation_id: str) -> MachineCommandResponse:
        try:
            record = self._operation_service.registry.request_cancel(operation_id)
            children = self._operation_service.registry.list_child_operations(operation_id)
            running_child = next((item for item in children if item.status == "running"), None)
            if running_child is not None:
                self._operation_service.registry.request_cancel(running_child.operation_id)
        except Exception as exc:
            return build_error_result(command="runs_cancel", exc=cast(Exception, exc))
        data: dict[str, Any] = {
            "operation_id": record.operation_id,
            "status": record.status,
            "cancel_requested": record.cancel_requested,
        }
        return build_success_result(command="runs_cancel", data=data)

    def get_operation_children(self, *, operation_id: str) -> MachineCommandResponse:
        try:
            self._operation_service.registry.get_operation(operation_id)
            items = self._operation_service.registry.list_child_operations(operation_id)
        except Exception as exc:
            return build_error_result(command="runs_children", exc=cast(Exception, exc))
        data = OperationChildrenData(
            operation_id=operation_id,
            items=[self._build_child_item(record) for record in items],
        )
        return build_success_result(
            command="runs_children",
            data=data.model_dump(mode="json"),
        )

    def reproduce_operation(self, *, operation_id: str) -> MachineCommandResponse:
        try:
            self._operation_service.registry.get_operation(operation_id)
            extra_artifacts, entries = self.materialize_reproduction(operation_id)
            updated_record = self._operation_service.registry.get_operation(operation_id)
        except Exception as exc:
            return build_error_result(command="runs_reproduce", exc=cast(Exception, exc))
        data: dict[str, Any] = {
            "operation_id": updated_record.operation_id,
            "status": updated_record.status,
            "verification_verdict": updated_record.verification_verdict,
            "reproduction_entries": [entry.model_dump(mode="json") for entry in entries],
        }
        data.update(self.artifact_summary(updated_record))
        artifacts = dict(updated_record.artifacts_json)
        artifacts.update(extra_artifacts)
        return build_success_result(command="runs_reproduce", data=data, artifacts=artifacts)

    def materialize_reproduction(
        self,
        operation_id: str,
    ) -> tuple[dict[str, str], list[Any]]:
        record = self._operation_service.registry.get_operation(operation_id)
        result = self._reproduction_service.materialize(record)
        extra_artifacts: dict[str, str] = {"repro_dir": str(result.repro_dir)}
        if result.entries:
            extra_artifacts["repro_original_request"] = str(result.entries[0].request_file)
        manifest_path = record.artifacts_json.get("artifact_manifest")
        if manifest_path:
            manifest = self._artifact_manifest_service.load_manifest(Path(manifest_path))
            updated_manifest = self._artifact_manifest_service.with_reproduction(
                manifest,
                reproduction=result.entries,
            )
            self._artifact_manifest_service.write_manifest(Path(manifest_path), updated_manifest)
            extra_artifacts["artifact_manifest"] = str(manifest_path)
        tracker = self._operation_service.get_tracker(operation_id)
        tracker.update_artifacts(extra_artifacts)
        return extra_artifacts, result.entries

    def artifact_summary(self, record) -> dict[str, Any]:  # noqa: ANN001
        manifest_path = cast(str | None, record.artifacts_json.get("artifact_manifest"))
        summary: dict[str, Any] = {
            "artifact_manifest_path": manifest_path,
            "repro_dir": record.artifacts_json.get("repro_dir"),
            "primary_artifact_ids": self._primary_artifact_ids(record.artifacts_json),
            "artifact_manifest_version": None,
            "schema_versions": {},
            "diagnostics_path": record.artifacts_json.get("diagnostics"),
            "duration_ms": None,
            "failure_category": None,
            "warning_summary": [],
            "token_usage": token_usage_from_result_json(record.result_json),
            "planning_usage": planning_usage_from_result_json(record.result_json),
            "execution_usage": execution_usage_from_result_json(record.result_json),
            "attempt_usages": attempt_usages_from_result_json(record.result_json),
        }
        if manifest_path:
            try:
                manifest = self._artifact_manifest_service.load_manifest(Path(manifest_path))
            except Exception:
                pass
            else:
                summary["artifact_manifest_version"] = manifest.manifest_version
                summary["schema_versions"] = dict(manifest.schema_versions)
                diagnostics_ref = manifest.primary_artifacts.get("diagnostics")
                if diagnostics_ref is not None:
                    summary["diagnostics_path"] = str(diagnostics_ref.path)
        diagnostics_path = cast(str | None, summary["diagnostics_path"])
        if diagnostics_path:
            summary.update(self._load_diagnostics_summary(Path(diagnostics_path)))
        return summary

    def _load_diagnostics_summary(self, path: Path) -> dict[str, Any]:
        try:
            diagnostics = self._diagnostics_service.load(path)
        except Exception:
            return {
                "diagnostics_path": str(path),
                "duration_ms": None,
                "failure_category": None,
                "warning_summary": [],
            }
        return {
            "diagnostics_path": str(path),
            "duration_ms": diagnostics.duration_ms,
            "failure_category": diagnostics.failure_category,
            "warning_summary": list(diagnostics.warning_summary),
        }

    def _primary_artifact_ids(self, artifacts: dict[str, str]) -> list[str]:
        manifest_path = artifacts.get("artifact_manifest")
        if manifest_path:
            try:
                manifest = self._artifact_manifest_service.load_manifest(Path(manifest_path))
            except Exception:
                pass
            else:
                return list(manifest.primary_artifacts)
        return [
            key
            for key in sorted(artifacts)
            if not key.startswith("case_")
            and key not in {"artifact_manifest", "repro_dir", "repro_original_request"}
        ]

    @staticmethod
    def _build_child_item(record: OperationRecord) -> OperationChildItemData:
        return OperationChildItemData(
            operation_id=record.operation_id,
            kind=record.kind,
            run_type=infer_run_type(record),
            plan_id=record.plan_id,
            case_id=record.case_id,
            title=infer_title(record),
            status=record.status,
            verification_verdict=record.verification_verdict,
            position_index=record.position_index,
            position_label=record.position_label,
            created_at=record.created_at,
            started_at=record.started_at,
            finished_at=record.finished_at,
            error_code=record.error_code,
            error_message=record.error_message,
            token_usage=cast(TokenUsageData | None, token_usage_data_from_result_json(record.result_json)),
        )

    @staticmethod
    def _build_batch_aggregate(children: list[OperationRecord]) -> BatchRunAggregateData:
        current = next((item for item in children if item.status == "running"), None)
        token_usage = merge_token_usages(token_usage_model_from_result_json(item.result_json) for item in children)
        return BatchRunAggregateData(
            total_children=len(children),
            queued_children=sum(1 for item in children if item.status == "queued"),
            running_children=sum(1 for item in children if item.status == "running"),
            succeeded_children=sum(1 for item in children if item.status == "succeeded"),
            failed_children=sum(1 for item in children if item.status == "failed"),
            cancelled_children=sum(1 for item in children if item.status == "cancelled"),
            completed_children=sum(1 for item in children if item.status in {"succeeded", "failed", "cancelled"}),
            current_child_operation_id=current.operation_id if current is not None else None,
            current_child_plan_id=current.plan_id if current is not None else None,
            current_child_case_id=current.case_id if current is not None else None,
            current_child_title=infer_title(current) if current is not None else None,
            token_usage=TokenUsageData.model_validate(token_usage.model_dump(mode="json")) if token_usage is not None else None,
        )

    @staticmethod
    def _infer_batch_kind(record: OperationRecord, children: list[OperationRecord]) -> str | None:
        if not children:
            return None
        if record.kind == "run_plans":
            return "single_device_multi_plan"
        if record.kind == "run_plan":
            return "single_plan_multi_case"
        return None


def token_usage_model_from_result_json(result_json: object) -> TokenUsage | None:
    payload = token_usage_from_result_json(result_json)
    if payload is None:
        return None
    try:
        return TokenUsage.model_validate(payload)
    except Exception:
        return None


def token_usage_data_from_result_json(result_json: object) -> TokenUsageData | None:
    payload = token_usage_from_result_json(result_json)
    if payload is None:
        return None
    try:
        return TokenUsageData.model_validate(payload)
    except Exception:
        return None
