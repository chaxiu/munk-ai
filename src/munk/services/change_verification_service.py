from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, cast
from uuid import uuid4

from munk.app import AppTarget
from munk.config import ResolvedConfig
from munk.execution.models import (
    ChangeVerificationRequest,
    ExecutedPlanResult,
    GeneratedPlanResult,
    PhasedOperationResult,
    PlanExecutionRequest,
    PlanExecutionResult,
)
from munk.planning.models import RequirementPlan
from munk.planning.service import PlanGenerationResult, PlanService
from munk.planning.storage import PlanStore
from munk.reporting.models import PLAN_REPAIR_REPORT_SCHEMA_VERSION, PlanRepairReport, UpstreamReviewLink
from munk.reporting.service import PlanReportService
from munk.reviewing.models import REVIEW_RESULT_SCHEMA_VERSION, ReviewResult
from munk.reviewing.orchestration_models import (
    REVIEW_ORCHESTRATION_SCHEMA_VERSION,
    ReviewOrchestrationContract,
    ReviewRequiredCase,
)
from munk.services.artifact_manifest_models import UpstreamReviewArtifacts
from munk.services.artifact_manifest_service import ArtifactManifestService
from munk.services.diagnostics_models import (
    OPERATION_DIAGNOSTICS_SCHEMA_VERSION,
    DiagnosticsFailureCategory,
    OperationDiagnostics,
)
from munk.services.diagnostics_service import OperationDiagnosticsService
from munk.services.operations.command_helpers import merge_scene_usages
from munk.services.plan_execution_service import PlanExecutionService
from munk.services.running.paths import create_unique_run_dir
from munk.services.running.service import RunService
from munk.testing import CaseBudget, CaseStartState, TestCase
from munk.token_usage import TokenUsage


def default_change_plan_id(prefix: str = "change") -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    return f"{prefix}-{timestamp}-{uuid4().hex[:8]}"


def _build_change_verification_plan_name(
    *,
    change_summary: str | None,
    planner_cases: list[TestCase],
    manual_cases: list[TestCase],
) -> str:
    if change_summary is not None and change_summary.strip():
        return change_summary.strip()
    first_case_title = next(
        (
            case.title.strip()
            for case in [*manual_cases, *planner_cases]
            if case.title.strip()
        ),
        None,
    )
    if first_case_title is not None:
        return first_case_title
    return "Change verification"


@dataclass(frozen=True)
class LoadedUpstreamReview:
    contract: ReviewOrchestrationContract
    review_result: ReviewResult
    review_orchestration_path: Path

    @property
    def review_result_path(self) -> Path:
        return self.review_result.review_result_path


class ChangeVerificationService:
    def __init__(
        self,
        *,
        resolved_config: ResolvedConfig,
        plan_service: PlanService | None = None,
        plan_execution_service: PlanExecutionService | None = None,
        plan_execution_service_factory: Callable[[], PlanExecutionService] | None = None,
        run_service_factory: Callable[[], RunService] | None = None,
        report_service: PlanReportService | None = None,
        plan_id_factory: Callable[[str], str] | None = None,
        operation_tracker=None,
        progress_callback: Callable[[str, str | None, dict[str, Any]], None] | None = None,
    ) -> None:
        self._resolved_config = resolved_config
        self._plan_service = plan_service or PlanService()
        self._plan_execution_service = plan_execution_service
        self._plan_execution_service_factory = plan_execution_service_factory
        self._run_service_factory = run_service_factory or (lambda: RunService(resolved_config=self._resolved_config))
        self._report_service = report_service or PlanReportService()
        self._plan_id_factory = plan_id_factory or default_change_plan_id
        self._operation_tracker = operation_tracker
        self._progress_callback = progress_callback
        self._artifact_manifest_service = ArtifactManifestService()
        self._diagnostics_service = OperationDiagnosticsService()

    def verify_change(self, request: ChangeVerificationRequest) -> PhasedOperationResult:
        started_at = datetime.now(timezone.utc).isoformat()
        timer_start = self._diagnostics_service.timer()
        self._append_operation_event("change_verification_started", "change verification started")
        upstream_review = None
        planner_cases: list[TestCase] = []
        result: PlanExecutionResult | None = None
        plan_result: GeneratedPlanResult | None = None
        planning_usage: TokenUsage | None = None
        try:
            plan, plan_result, upstream_review, planner_cases, planning_usage = self._prepare_plan(
                request,
            )
            if not request.auto_run:
                return PhasedOperationResult(
                    app_id=request.app_id,
                    plan_id=plan.plan_id,
                    plan_name=plan.name,
                    phase="planned",
                    plan_result=plan_result,
                    planning_usage=cast(TokenUsage | None, planning_usage),
                    total_usage=cast(TokenUsage | None, planning_usage),
                )
            if request.app_target is None:
                raise ValueError("app_target must not be empty when auto_run is true")
            execution_request = PlanExecutionRequest(
                app_id=request.app_id,
                plan_id=plan.plan_id,
                app_target=cast(AppTarget, request.app_target),
                device_ref=request.device_ref,
                artifact_path=request.artifact_path,
                assets_root=request.assets_root,
                runtime_overrides=dict(request.runtime_overrides),
                fail_fast=False,
            )
            result = self._build_plan_execution_service().execute_plan_model(plan, execution_request)
            if upstream_review is not None:
                self._attach_upstream_review_outputs(
                    result=result,
                    upstream_review=upstream_review,
                )
            result = self._attach_diagnostics(
                request=request,
                result=result,
                upstream_review=upstream_review,
                planner_case_count=len(planner_cases),
                started_at=started_at,
                duration_ms=self._diagnostics_service.elapsed_ms(timer_start),
            )
            return PhasedOperationResult(
                app_id=request.app_id,
                plan_id=plan.plan_id,
                plan_name=plan.name,
                phase="executed",
                plan_result=plan_result,
                execution_result=self._build_executed_plan_result(
                    result=result,
                    upstream_review=upstream_review,
                ),
                planning_usage=cast(TokenUsage | None, planning_usage),
                execution_usage=result.token_usage,
                total_usage=merge_scene_usages(cast(TokenUsage | None, planning_usage), result.token_usage),
            )
        except Exception as exc:
            failure_dir = self._resolve_failure_dir(request)
            diagnostics_path = failure_dir / "diagnostics.json"
            diagnostics = self._build_verify_diagnostics(
                request=request,
                result=result,
                upstream_review=upstream_review,
                planner_case_count=len(planner_cases),
                started_at=started_at,
                duration_ms=self._diagnostics_service.elapsed_ms(timer_start),
                status="failed",
                failure_category=self._diagnostics_service.classify_exception(exc),
                failure_stage="change_verification",
                failure_message=str(exc),
            )
            self._diagnostics_service.write(diagnostics_path, diagnostics)
            tracker = self._operation_tracker
            if tracker is not None and hasattr(tracker, "update_artifacts"):
                tracker.update_artifacts({"diagnostics": str(diagnostics_path)})
            raise

    def _prepare_plan(
        self,
        request: ChangeVerificationRequest,
    ) -> tuple[RequirementPlan, GeneratedPlanResult, LoadedUpstreamReview | None, list[TestCase], TokenUsage | None]:
        upstream_review = self._load_review_contract(request)
        review_contract = upstream_review.contract if upstream_review is not None else None
        self._append_operation_event(
            "change_verification_review_contract_loaded",
            "change verification review contract loaded",
            {
                "app_id": request.app_id,
                "review_hint_enabled": review_contract is not None,
                "review_required_case_count": len(review_contract.required_cases) if review_contract else 0,
            },
        )
        manual_cases = list(request.provided_cases)
        if review_contract is not None:
            manual_cases.extend(
                _to_test_case(case)
                for case in review_contract.required_cases
            )
        planner_result = self._generate_planner_cases(request) if request.enable_plan_agent else None
        planner_cases = list(planner_result.plan.cases) if planner_result is not None else []
        self._append_operation_event(
            "change_verification_cases_ready",
            "change verification cases prepared",
            {
                "manual_case_count": len(request.provided_cases),
                "review_required_case_count": len(review_contract.required_cases) if review_contract else 0,
                "planner_case_count": len(planner_cases),
                "review_hint_enabled": review_contract is not None,
            },
        )
        plan = self._build_runtime_plan(
            app_id=request.app_id,
            change_summary=request.change_summary,
            manual_cases=manual_cases,
            planner_cases=planner_cases,
        )
        plan_result = self._save_plan(
            plan,
            assets_root=request.assets_root,
            planning_usage=planner_result.planning_usage if planner_result is not None else None,
        )
        self._append_operation_event(
            "change_verification_plan_saved",
            "change verification plan saved",
            {
                "app_id": request.app_id,
                "plan_id": plan.plan_id,
                "case_count": len(plan.cases),
                "plan_path": str(plan_result.plan_path),
                "snapshot_path": str(plan_result.snapshot_path),
                "planning_usage": (
                    plan_result.planning_usage.model_dump(mode="json")
                    if plan_result.planning_usage is not None
                    else None
                ),
            },
        )
        return plan, plan_result, upstream_review, planner_cases, plan_result.planning_usage

    def _generate_planner_cases(self, request: ChangeVerificationRequest) -> PlanGenerationResult:
        return self._plan_service.generate_change_plan(
            request.to_change_plan_input(),
            resolved_config=self._resolved_config,
            cancel_checker=self._cancel_checker,
            progress_callback=self._append_operation_event,
        )

    def _build_runtime_plan(
        self,
        *,
        app_id: str,
        change_summary: str | None,
        manual_cases: list[TestCase],
        planner_cases: list[TestCase],
    ) -> RequirementPlan:
        merged_cases = list(manual_cases)
        seen_case_ids = {case.case_id for case in manual_cases}
        for case in planner_cases:
            if case.case_id in seen_case_ids:
                continue
            merged_cases.append(case)
            seen_case_ids.add(case.case_id)
        prefix = "mixed" if manual_cases and planner_cases else ("manual" if manual_cases else "change")
        return RequirementPlan(
            plan_id=self._plan_id_factory(prefix),
            name=_build_change_verification_plan_name(
                change_summary=change_summary,
                planner_cases=planner_cases,
                manual_cases=manual_cases,
            ),
            app_id=app_id,
            source="change_verification",
            version="phase6.v1",
            cases=merged_cases,
        )

    @staticmethod
    def _save_plan(
        plan: RequirementPlan,
        *,
        assets_root: Path | None,
        planning_usage: TokenUsage | None = None,
    ) -> GeneratedPlanResult:
        plan_store = PlanStore(assets_root)
        plan_path = plan_store.save(plan)
        snapshot_path = plan_store.export_snapshot(plan)
        return GeneratedPlanResult(
            plan_name=plan.name,
            case_count=len(plan.cases),
            plan_path=plan_path,
            snapshot_path=snapshot_path,
            planning_usage=planning_usage,
        )

    def _build_plan_execution_service(self) -> PlanExecutionService:
        if self._plan_execution_service is not None:
            return self._plan_execution_service
        if self._plan_execution_service_factory is not None:
            return self._plan_execution_service_factory()
        return PlanExecutionService(
            resolved_config=self._resolved_config,
            run_service_factory=self._run_service_factory,
            report_service=self._report_service,
            operation_tracker=self._operation_tracker,
        )

    def _cancel_checker(self) -> bool:
        tracker = self._operation_tracker
        if tracker is None:
            return False
        return tracker.should_cancel()

    def _append_operation_event(
        self,
        event_type: str,
        message: str | None,
        data: dict[str, Any] | None = None,
    ) -> None:
        payload = data or {}
        progress_callback = self._progress_callback
        if progress_callback is not None:
            progress_callback(event_type, message, payload)
            return
        tracker = self._operation_tracker
        if tracker is not None:
            tracker.append_event(event_type=event_type, message=message, data=payload)

    def _load_review_contract(
        self,
        request: ChangeVerificationRequest,
    ) -> LoadedUpstreamReview | None:
        if request.review_orchestration_path is None:
            return None
        review_orchestration_path = request.review_orchestration_path
        contract = ReviewOrchestrationContract.model_validate_json(
            review_orchestration_path.read_text(encoding="utf-8")
        )
        review_result_path = review_orchestration_path.parent / "review_result.json"
        review_result = ReviewResult.model_validate_json(review_result_path.read_text(encoding="utf-8"))
        return LoadedUpstreamReview(
            contract=contract,
            review_result=review_result,
            review_orchestration_path=review_orchestration_path,
        )

    def _attach_upstream_review_outputs(
        self,
        *,
        result: PlanExecutionResult,
        upstream_review: LoadedUpstreamReview,
    ) -> None:
        plan_run_dir = result.summary_path.parent
        upstream_review_path = plan_run_dir / "upstream_review_result.json"
        upstream_orchestration_path = plan_run_dir / "review_orchestration.json"
        shutil.copyfile(upstream_review.review_result_path, upstream_review_path)
        upstream_orchestration_path.write_text(
            upstream_review.contract.model_dump_json(indent=2),
            encoding="utf-8",
        )
        report = PlanRepairReport.model_validate_json(result.report_path.read_text(encoding="utf-8"))
        upstream_review_link = self._build_upstream_review_link(
            upstream_review=upstream_review,
            upstream_review_path=upstream_review_path,
            upstream_orchestration_path=upstream_orchestration_path,
        )
        report = report.model_copy(update={"upstream_review": upstream_review_link})
        result.report_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        manifest_path = plan_run_dir / "artifact_manifest.json"
        manifest = self._artifact_manifest_service.load_manifest(manifest_path)
        primary_artifacts = dict(manifest.primary_artifacts)
        primary_artifacts["upstream_review_result"] = self._artifact_manifest_service.build_artifact_refs(
            artifacts={"upstream_review_result": str(upstream_review_path)},
            scope="plan_run",
        )["upstream_review_result"]
        primary_artifacts["review_orchestration"] = self._artifact_manifest_service.build_artifact_refs(
            artifacts={"review_orchestration": str(upstream_orchestration_path)},
            scope="plan_run",
        )["review_orchestration"]
        updated_manifest = manifest.model_copy(
            update={
                "manifest_version": max(manifest.manifest_version, 2),
                "primary_artifacts": primary_artifacts,
                "schema_versions": {
                    **manifest.schema_versions,
                    "review_result": REVIEW_RESULT_SCHEMA_VERSION,
                    "review_orchestration": upstream_review.contract.schema_version,
                    "plan_repair_report": report.schema_version,
                },
                "upstream_review": UpstreamReviewArtifacts(
                    review_operation_id=upstream_review.review_result.operation_id,
                    review_result_path=upstream_review_path,
                    review_orchestration_path=upstream_orchestration_path,
                    contract_version=upstream_review.contract.schema_version,
                ),
            }
        )
        self._artifact_manifest_service.write_manifest(manifest_path, updated_manifest)

    def _attach_diagnostics(
        self,
        *,
        request: ChangeVerificationRequest,
        result: PlanExecutionResult,
        upstream_review: LoadedUpstreamReview | None,
        planner_case_count: int,
        started_at: str,
        duration_ms: int,
    ) -> PlanExecutionResult:
        plan_run_dir = result.summary_path.parent
        diagnostics_path = plan_run_dir / "diagnostics.json"
        diagnostics = self._build_verify_diagnostics(
            request=request,
            result=result,
            upstream_review=upstream_review,
            planner_case_count=planner_case_count,
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
        primary_artifacts = dict(manifest.primary_artifacts)
        primary_artifacts["diagnostics"] = self._artifact_manifest_service.build_artifact_refs(
            artifacts={"diagnostics": str(diagnostics_path)},
            scope="plan_run",
        )["diagnostics"]
        updated_manifest = manifest.model_copy(
            update={
                "manifest_version": max(manifest.manifest_version, 2),
                "primary_artifacts": primary_artifacts,
                "schema_versions": {
                    **manifest.schema_versions,
                    "operation_diagnostics": OPERATION_DIAGNOSTICS_SCHEMA_VERSION,
                },
                "metadata": {
                    **manifest.metadata,
                    "duration_ms": diagnostics.duration_ms,
                    "failure_category": diagnostics.failure_category,
                },
            }
        )
        self._artifact_manifest_service.write_manifest(manifest_path, updated_manifest)

        tracker = self._operation_tracker
        if tracker is not None and hasattr(tracker, "update_artifacts"):
            tracker.update_artifacts({"diagnostics": str(diagnostics_path)})
        return result.model_copy(update={"diagnostics_path": diagnostics_path})

    def _build_verify_diagnostics(
        self,
        *,
        request: ChangeVerificationRequest,
        result: PlanExecutionResult | None,
        upstream_review: LoadedUpstreamReview | None,
        planner_case_count: int,
        started_at: str,
        duration_ms: int,
        status: str,
        failure_category: DiagnosticsFailureCategory | None,
        failure_stage: str | None,
        failure_message: str | None,
    ) -> OperationDiagnostics:
        provider, model, role_models, config_fingerprint = self._diagnostics_service.resolve_provider_model(
            resolved_config=self._resolved_config,
            roles=("plan", "runner", "judge"),
        )
        plan_run_dir = self._resolve_failure_dir(request) if result is None else result.summary_path.parent
        summary_path = plan_run_dir / "plan_execution.json"
        report_path = plan_run_dir / "report.json"
        manifest_path = plan_run_dir / "artifact_manifest.json"
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
                artifact_id="artifact_manifest",
                path=manifest_path,
                required_fields=("manifest_version", "primary_artifacts"),
            ),
        ]
        linked_operation_ids = {}
        if upstream_review is not None:
            upstream_review_path = plan_run_dir / "upstream_review_result.json"
            upstream_orchestration_path = plan_run_dir / "review_orchestration.json"
            checks.append(
                self._diagnostics_service.build_json_artifact_check(
                    artifact_id="upstream_review_result",
                    path=upstream_review_path,
                    required_fields=("risk_summary", "findings"),
                    expected_schema_version=REVIEW_RESULT_SCHEMA_VERSION,
                )
            )
            checks.append(
                self._diagnostics_service.build_json_artifact_check(
                    artifact_id="review_orchestration",
                    path=upstream_orchestration_path,
                    required_fields=("review_hints", "required_cases"),
                    expected_schema_version=upstream_review.contract.schema_version,
                )
            )
            linked_operation_ids["upstream_review_operation_id"] = upstream_review.review_result.operation_id
        warning_summary: list[str] = []
        failed_artifacts = self._diagnostics_service.failed_artifact_count(checks)
        if failed_artifacts:
            warning_summary.append(f"{failed_artifacts} required artifacts failed validation")
        if upstream_review is None:
            warning_summary.append("upstream review linkage disabled")
        finished_at = datetime.now(timezone.utc).isoformat()
        contract_versions: dict[str, str] = {}
        if manifest_path.exists():
            try:
                manifest = self._artifact_manifest_service.load_manifest(manifest_path)
            except Exception:
                pass
            else:
                contract_versions.update(manifest.schema_versions)
        if not contract_versions and result is not None:
            contract_versions["plan_repair_report"] = PLAN_REPAIR_REPORT_SCHEMA_VERSION
            if upstream_review is not None:
                contract_versions["review_result"] = REVIEW_RESULT_SCHEMA_VERSION
                contract_versions["review_orchestration"] = upstream_review.contract.schema_version
        return OperationDiagnostics(
            operation_id=self._operation_id(),
            operation_kind="verify_change",
            app_id=request.app_id,
            status="succeeded" if status == "succeeded" else "failed",
            verification_verdict=None if result is None else _verdict_for_plan_status(result.status),
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            provider=provider,
            model=model,
            role_models=role_models,
            config_fingerprint=config_fingerprint,
            device_ref=request.device_ref,
            entry_identity=request.app_target.entry_identity if request.app_target is not None else None,
            warning_summary=warning_summary,
            failure_category=failure_category,
            failure_stage=failure_stage,
            failure_message=failure_message,
            artifact_checks=checks,
            contract_versions=contract_versions,
            linked_operation_ids=linked_operation_ids,
        )

    @staticmethod
    def _build_executed_plan_result(
        *,
        result: PlanExecutionResult,
        upstream_review: LoadedUpstreamReview | None,
    ) -> ExecutedPlanResult:
        upstream_review_result_path = result.summary_path.parent / "upstream_review_result.json"
        upstream_review_orchestration_path = result.summary_path.parent / "review_orchestration.json"
        diagnostics_path = result.diagnostics_path
        duration_ms = None
        failure_category = None
        warning_summary: list[str] = []
        contract_versions: dict[str, str | None] = {}
        artifact_manifest_version = None
        if diagnostics_path is not None:
            diagnostics = OperationDiagnosticsService().load(diagnostics_path)
            duration_ms = diagnostics.duration_ms
            failure_category = diagnostics.failure_category
            warning_summary = list(diagnostics.warning_summary)
        manifest_path = result.summary_path.parent / "artifact_manifest.json"
        if manifest_path.exists():
            try:
                manifest = ArtifactManifestService().load_manifest(manifest_path)
            except Exception:
                pass
            else:
                contract_versions = dict(manifest.schema_versions)
                artifact_manifest_version = manifest.manifest_version
        if upstream_review is not None and "review_orchestration" not in contract_versions:
            contract_versions["review_orchestration"] = upstream_review.contract.schema_version
        return ExecutedPlanResult(
            verification_status=result.status,
            total_cases=result.total_cases,
            passed_cases=result.passed_cases,
            failed_cases=result.failed_cases,
            inconclusive_cases=result.inconclusive_cases,
            stopped_early=result.stopped_early,
            items=list(result.items),
            summary_path=result.summary_path,
            report_path=result.report_path,
            diagnostics_path=result.diagnostics_path,
            duration_ms=duration_ms,
            failure_category=failure_category,
            warning_summary=warning_summary,
            upstream_review_enabled=upstream_review_result_path.exists(),
            upstream_review_result_path=upstream_review_result_path if upstream_review_result_path.exists() else None,
            upstream_review_orchestration_path=(
                upstream_review_orchestration_path if upstream_review_orchestration_path.exists() else None
            ),
            contract_versions=contract_versions,
            artifact_manifest_version=artifact_manifest_version,
            token_usage=result.token_usage,
        )

    @staticmethod
    def _resolve_failure_dir(request: ChangeVerificationRequest) -> Path:
        if request.artifact_path is not None:
            request.artifact_path.mkdir(parents=True, exist_ok=True)
            return request.artifact_path
        return create_unique_run_dir(prefix="verify_change_run")

    def _operation_id(self) -> str | None:
        tracker = self._operation_tracker
        if tracker is None:
            return None
        try:
            return tracker.get_record().operation_id
        except Exception:
            return getattr(tracker, "operation_id", None)

    @staticmethod
    def _build_upstream_review_link(
        *,
        upstream_review: LoadedUpstreamReview,
        upstream_review_path: Path,
        upstream_orchestration_path: Path,
    ) -> UpstreamReviewLink:
        return UpstreamReviewLink(
            review_operation_id=upstream_review.review_result.operation_id,
            review_orchestration_path=upstream_orchestration_path,
            review_result_path=upstream_review_path,
            risk_summary=upstream_review.contract.review_hints.risk_summary,
            high_risk_count=upstream_review.contract.statistics.high_risk_count,
            finding_titles=[item.title for item in upstream_review.contract.review_hints.high_risk_findings],
            required_case_ids=[item.case_id for item in upstream_review.contract.required_cases],
            advisory_case_titles=[item.title for item in upstream_review.contract.advisory_cases],
            contract_version=upstream_review.contract.schema_version or REVIEW_ORCHESTRATION_SCHEMA_VERSION,
        )


def _verdict_for_plan_status(
    status: str,
) -> Literal["passed", "failed", "inconclusive"] | None:
    if status == "failed":
        return "failed"
    if status in {"inconclusive", "stopped"}:
        return "inconclusive"
    if status == "passed":
        return "passed"
    return None


def _to_test_case(case: ReviewRequiredCase) -> TestCase:
    return TestCase(
        case_id=case.case_id,
        title=case.title,
        intent=case.intent,
        preconditions=list(case.preconditions),
        expected=list(case.expected),
        is_core_case=case.is_core_case,
        runner_goal=case.runner_goal,
        budget=(
            None
            if case.budget is None
            else CaseBudget(
                max_steps=case.budget.max_steps,
                max_seconds=case.budget.max_seconds,
            )
        ),
        start_state=CaseStartState(
            mode=case.start_state.mode,
            page_id=case.start_state.page_id,
        ),
    )
