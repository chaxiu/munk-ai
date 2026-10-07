from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from munk.app import AppTarget
from munk.artifacts import ARTIFACT_ID_ARTIFACT_MANIFEST, ARTIFACT_ID_DIAGNOSTICS
from munk.config import ResolvedConfig
from munk.execution.models import ChangeVerificationRequest, PlanExecutionResult
from munk.reporting.models import PLAN_REPAIR_REPORT_SCHEMA_VERSION, PlanRepairReport
from munk.reviewing.models import REVIEW_RESULT_SCHEMA_VERSION
from munk.services.artifact_manifest_models import ArtifactSchemaVersions
from munk.services.artifact_manifest_service import ArtifactManifestService
from munk.services.change_verification_results import LoadedUpstreamReview
from munk.services.diagnostics_models import (
    OPERATION_DIAGNOSTICS_SCHEMA_VERSION,
    DiagnosticsFailureCategory,
    OperationDiagnostics,
)
from munk.services.diagnostics_service import OperationDiagnosticsService
from munk.services.running.paths import create_unique_run_dir


class ChangeVerificationDiagnosticsManager:
    def __init__(
        self,
        *,
        resolved_config: ResolvedConfig,
        artifact_manifest_service: ArtifactManifestService | None = None,
        diagnostics_service: OperationDiagnosticsService | None = None,
        operation_id_provider: Callable[[], str | None] | None = None,
        artifact_updater: Callable[[dict[str, str]], None] | None = None,
    ) -> None:
        self._resolved_config = resolved_config
        self._artifact_manifest_service = artifact_manifest_service or ArtifactManifestService()
        self._diagnostics_service = diagnostics_service or OperationDiagnosticsService()
        self._operation_id_provider = operation_id_provider or (lambda: None)
        self._artifact_updater = artifact_updater or (lambda artifacts: None)

    def attach_diagnostics(
        self,
        *,
        request: ChangeVerificationRequest,
        result: PlanExecutionResult,
        upstream_review: LoadedUpstreamReview | None,
        started_at: str,
        duration_ms: int,
    ) -> PlanExecutionResult:
        plan_run_dir = result.summary_path.parent
        diagnostics_path = plan_run_dir / "diagnostics.json"
        diagnostics = self._build_verify_diagnostics(
            request=request,
            result=result,
            upstream_review=upstream_review,
            started_at=started_at,
            duration_ms=duration_ms,
            status="succeeded",
            failure_category=None,
            failure_stage=None,
            failure_message=None,
        )
        self._diagnostics_service.write(diagnostics_path, diagnostics)

        report = PlanRepairReport.model_validate_json(result.report_path.read_text(encoding="utf-8"))
        report = report.model_copy(
            update={
                "metadata": {
                    **report.metadata,
                    "diagnostics_path": str(diagnostics_path),
                    "failure_category": diagnostics.failure_category,
                    "warning_summary": list(diagnostics.warning_summary),
                }
            }
        )
        result.report_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")

        manifest_path = plan_run_dir / "artifact_manifest.json"
        manifest = self._artifact_manifest_service.load_manifest(manifest_path)
        updated_manifest = self._artifact_manifest_service.augment_manifest(
            manifest,
            primary_artifacts={ARTIFACT_ID_DIAGNOSTICS: str(diagnostics_path)},
            schema_versions=ArtifactSchemaVersions(
                operation_diagnostics=OPERATION_DIAGNOSTICS_SCHEMA_VERSION,
            ),
        )
        self._artifact_manifest_service.write_manifest(manifest_path, updated_manifest)
        self._artifact_updater({ARTIFACT_ID_DIAGNOSTICS: str(diagnostics_path)})
        return result.model_copy(update={"diagnostics_path": diagnostics_path})

    def write_failure_diagnostics(
        self,
        *,
        request: ChangeVerificationRequest,
        result: PlanExecutionResult | None,
        upstream_review: LoadedUpstreamReview | None,
        started_at: str,
        duration_ms: int,
        failure_category: DiagnosticsFailureCategory | None,
        failure_stage: str | None,
        failure_message: str | None,
    ) -> Path:
        failure_dir = resolve_verify_failure_dir(result=result)
        diagnostics_path = failure_dir / "diagnostics.json"
        diagnostics = self._build_verify_diagnostics(
            request=request,
            result=result,
            upstream_review=upstream_review,
            started_at=started_at,
            duration_ms=duration_ms,
            status="failed",
            failure_category=failure_category,
            failure_stage=failure_stage,
            failure_message=failure_message,
            plan_run_dir=failure_dir,
        )
        self._diagnostics_service.write(diagnostics_path, diagnostics)
        self._artifact_updater({ARTIFACT_ID_DIAGNOSTICS: str(diagnostics_path)})
        return diagnostics_path

    def _build_verify_diagnostics(
        self,
        *,
        request: ChangeVerificationRequest,
        result: PlanExecutionResult | None,
        upstream_review: LoadedUpstreamReview | None,
        started_at: str,
        duration_ms: int,
        status: str,
        failure_category: DiagnosticsFailureCategory | None,
        failure_stage: str | None,
        failure_message: str | None,
        plan_run_dir: Path | None = None,
    ) -> OperationDiagnostics:
        provider, model, role_models, config_fingerprint = self._diagnostics_service.resolve_provider_model(
            resolved_config=self._resolved_config,
            roles=("plan", "runner", "judge"),
        )
        resolved_plan_run_dir = plan_run_dir or resolve_verify_failure_dir(result=result)
        summary_path = resolved_plan_run_dir / "plan_execution.json"
        report_path = resolved_plan_run_dir / "report.json"
        manifest_path = resolved_plan_run_dir / "artifact_manifest.json"
        checks = [
            self._diagnostics_service.build_json_artifact_check(
                artifact_id="plan_execution",
                path=summary_path,
                required_fields=("status", "items"),
            ),
            self._diagnostics_service.build_json_artifact_check(
                artifact_id="report",
                path=report_path,
                required_fields=("schema_version", "overall_verdict", "totals"),
            ),
            self._diagnostics_service.build_json_artifact_check(
                artifact_id=ARTIFACT_ID_ARTIFACT_MANIFEST,
                path=manifest_path,
                required_fields=("manifest_version", "primary_artifacts"),
            ),
        ]
        linked_operation_ids: dict[str, str | None] = {}
        if upstream_review is not None:
            checks.extend(
                [
                    self._diagnostics_service.build_json_artifact_check(
                        artifact_id="upstream_review_result",
                        path=resolved_plan_run_dir / "upstream_review_result.json",
                        required_fields=("risk_summary", "findings"),
                        expected_schema_version=REVIEW_RESULT_SCHEMA_VERSION,
                    ),
                    self._diagnostics_service.build_json_artifact_check(
                        artifact_id="review_orchestration",
                        path=resolved_plan_run_dir / "review_orchestration.json",
                        required_fields=("review_hints", "required_cases"),
                        expected_schema_version=upstream_review.contract.schema_version,
                    ),
                ]
            )
            linked_operation_ids["upstream_review_operation_id"] = upstream_review.review_result.operation_id

        warning_summary = _build_warning_summary(
            checks=checks,
            diagnostics_service=self._diagnostics_service,
            upstream_review=upstream_review,
        )
        contract_versions = _load_contract_versions(
            manifest_path=manifest_path,
            result=result,
            upstream_review=upstream_review,
            artifact_manifest_service=self._artifact_manifest_service,
        )
        app_target = request.app_target
        return OperationDiagnostics(
            operation_id=self._operation_id_provider(),
            operation_kind="verify_change",
            app_id=request.app_id,
            status="succeeded" if status == "succeeded" else "failed",
            verification_verdict=None if result is None else _verdict_for_plan_status(result.status),
            started_at=started_at,
            finished_at=datetime.now(timezone.utc).isoformat(),
            duration_ms=duration_ms,
            provider=provider,
            model=model,
            role_models=role_models,
            config_fingerprint=config_fingerprint,
            device_ref=request.device_ref,
            entry_identity=_entry_identity(app_target),
            warning_summary=warning_summary,
            failure_category=failure_category,
            failure_stage=failure_stage,
            failure_message=failure_message,
            artifact_checks=checks,
            contract_versions=contract_versions,
            linked_operation_ids=linked_operation_ids,
        )


def _entry_identity(app_target: AppTarget | None) -> str | None:
    if app_target is None:
        return None
    return app_target.entry_identity


def _build_warning_summary(
    *,
    checks: list,
    diagnostics_service: OperationDiagnosticsService,
    upstream_review: LoadedUpstreamReview | None,
) -> list[str]:
    warning_summary: list[str] = []
    failed_artifacts = diagnostics_service.failed_artifact_count(checks)
    if failed_artifacts:
        warning_summary.append(f"{failed_artifacts} required artifacts failed validation")
    if upstream_review is None:
        warning_summary.append("upstream review linkage disabled")
    return warning_summary


def _load_contract_versions(
    *,
    manifest_path: Path,
    result: PlanExecutionResult | None,
    upstream_review: LoadedUpstreamReview | None,
    artifact_manifest_service: ArtifactManifestService,
) -> dict[str, str]:
    contract_versions: dict[str, str] = {}
    if manifest_path.exists():
        try:
            manifest = artifact_manifest_service.load_manifest(manifest_path)
        except Exception:
            pass
        else:
            contract_versions.update(manifest.schema_versions.to_mapping())
    if not contract_versions and result is not None:
        contract_versions["plan_repair_report"] = PLAN_REPAIR_REPORT_SCHEMA_VERSION
        if upstream_review is not None:
            contract_versions["review_result"] = REVIEW_RESULT_SCHEMA_VERSION
            contract_versions["review_orchestration"] = upstream_review.contract.schema_version
    return contract_versions


def resolve_verify_failure_dir(*, result: PlanExecutionResult | None) -> Path:
    """Resolve the directory for verify_change failure diagnostics.

    ChangeVerificationRequest.artifact_path is an *input* installable (APK/IPA/bundle),
    the same semantics as PlanExecutionRequest / CaseExecutionRequest. It is not an
    operation output root (unlike ReviewRequest.artifact_path).

    Prefer co-locating diagnostics with plan-execution outputs when a result exists;
    otherwise allocate a dedicated verify failure run directory.
    """
    if result is not None:
        return result.summary_path.parent
    return create_unique_run_dir(prefix="verify_change_run")


def _verdict_for_plan_status(status: str) -> str | None:
    if status == "failed":
        return "failed"
    if status in {"inconclusive", "stopped"}:
        return "inconclusive"
    if status == "passed":
        return "passed"
    return None
