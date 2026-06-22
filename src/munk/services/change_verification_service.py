from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from munk.config import ResolvedConfig
from munk.execution.models import (
    ChangeVerificationRequest,
    GeneratedPlanResult,
    PhasedOperationResult,
    PlanExecutionRequest,
    PlanExecutionResult,
)
from munk.planning.models import RequirementPlan
from munk.planning.service import PlanGenerationResult, PlanService
from munk.planning.storage import PlanStore
from munk.reporting.service import PlanReportService
from munk.reviewing.orchestration_models import ReviewRequiredCase
from munk.services.artifact_manifest_service import ArtifactManifestService
from munk.services.change_verification_diagnostics import ChangeVerificationDiagnosticsManager
from munk.services.change_verification_results import (
    ChangeVerificationResultService,
    LoadedUpstreamReview,
    load_upstream_review,
)
from munk.services.change_verification_support import (
    ChangeVerificationProgressCallback,
    ChangeVerificationProgressReporter,
    SupportsChangeVerificationTracker,
)
from munk.services.diagnostics_service import OperationDiagnosticsService
from munk.services.operations.command_helpers import merge_scene_usages
from munk.services.plan_execution_service import PlanExecutionService
from munk.services.running.service import RunService
from munk.services.verify_change_event_payloads import (
    build_change_verification_cases_ready_payload,
    build_change_verification_plan_saved_payload,
    build_change_verification_review_contract_loaded_payload,
)
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
        operation_tracker: SupportsChangeVerificationTracker | None = None,
        progress_callback: ChangeVerificationProgressCallback | None = None,
    ) -> None:
        self._resolved_config = resolved_config
        self._plan_service = plan_service or PlanService()
        self._plan_execution_service = plan_execution_service
        self._plan_execution_service_factory = plan_execution_service_factory
        self._run_service_factory = run_service_factory or (lambda: RunService(resolved_config=self._resolved_config))
        self._report_service = report_service or PlanReportService()
        self._plan_id_factory = plan_id_factory or default_change_plan_id
        self._operation_tracker = operation_tracker
        self._artifact_manifest_service = ArtifactManifestService()
        self._diagnostics_service = OperationDiagnosticsService()
        self._progress_reporter = ChangeVerificationProgressReporter(
            tracker=operation_tracker,
            progress_callback=progress_callback,
        )
        self._result_service = ChangeVerificationResultService(
            artifact_manifest_service=self._artifact_manifest_service,
            diagnostics_service=self._diagnostics_service,
        )
        self._diagnostics_manager = ChangeVerificationDiagnosticsManager(
            resolved_config=self._resolved_config,
            artifact_manifest_service=self._artifact_manifest_service,
            diagnostics_service=self._diagnostics_service,
            operation_id_provider=self._progress_reporter.operation_id,
            artifact_updater=self._progress_reporter.update_artifacts,
        )

    def verify_change(self, request: ChangeVerificationRequest) -> PhasedOperationResult:
        started_at = datetime.now(timezone.utc).isoformat()
        timer_start = self._diagnostics_service.timer()
        self._progress_reporter.append_event(
            "change_verification_started",
            "change verification started",
        )
        upstream_review = None
        result: PlanExecutionResult | None = None
        plan_result: GeneratedPlanResult | None = None
        planning_usage: TokenUsage | None = None
        try:
            plan, plan_result, upstream_review, planning_usage = self._prepare_plan(
                request,
            )
            if not request.auto_run:
                return PhasedOperationResult(
                    app_id=request.app_id,
                    plan_id=plan.plan_id,
                    plan_name=plan.name,
                    phase="planned",
                    plan_result=plan_result,
                    planning_usage=planning_usage,
                    total_usage=planning_usage,
                )
            if request.app_target is None:
                raise ValueError("app_target must not be empty when auto_run is true")
            execution_request = PlanExecutionRequest(
                app_id=request.app_id,
                plan_id=plan.plan_id,
                app_target=request.app_target,
                device_ref=request.device_ref,
                artifact_path=request.artifact_path,
                assets_root=request.assets_root,
                runtime_overrides=dict(request.runtime_overrides),
                fail_fast=request.fail_fast,
            )
            result = self._build_plan_execution_service().execute_plan_model(plan, execution_request)
            if upstream_review is not None:
                self._result_service.attach_upstream_review_outputs(
                    result=result,
                    upstream_review=upstream_review,
                )
            result = self._diagnostics_manager.attach_diagnostics(
                request=request,
                result=result,
                upstream_review=upstream_review,
                started_at=started_at,
                duration_ms=self._diagnostics_service.elapsed_ms(timer_start),
            )
            return PhasedOperationResult(
                app_id=request.app_id,
                plan_id=plan.plan_id,
                plan_name=plan.name,
                phase="executed",
                plan_result=plan_result,
                execution_result=self._result_service.build_executed_plan_result(
                    result=result,
                    upstream_review=upstream_review,
                ),
                planning_usage=planning_usage,
                execution_usage=result.token_usage,
                total_usage=merge_scene_usages(planning_usage, result.token_usage),
            )
        except Exception as exc:
            self._diagnostics_manager.write_failure_diagnostics(
                request=request,
                result=result,
                upstream_review=upstream_review,
                started_at=started_at,
                duration_ms=self._diagnostics_service.elapsed_ms(timer_start),
                failure_category=self._diagnostics_service.classify_exception(exc),
                failure_stage="change_verification",
                failure_message=str(exc),
            )
            raise

    def _prepare_plan(
        self,
        request: ChangeVerificationRequest,
    ) -> tuple[RequirementPlan, GeneratedPlanResult, LoadedUpstreamReview | None, TokenUsage | None]:
        upstream_review = load_upstream_review(request.review_orchestration_path)
        review_contract = upstream_review.contract if upstream_review is not None else None
        self._progress_reporter.append_event(
            "change_verification_review_contract_loaded",
            "change verification review contract loaded",
            build_change_verification_review_contract_loaded_payload(
                app_id=request.app_id,
                review_hint_enabled=review_contract is not None,
                review_required_case_count=len(review_contract.required_cases) if review_contract else 0,
            ),
        )
        manual_cases = list(request.provided_cases)
        if review_contract is not None:
            manual_cases.extend(
                _to_test_case(case)
                for case in review_contract.required_cases
            )
        planner_result = self._generate_planner_cases(request) if request.enable_plan_agent else None
        planner_cases = list(planner_result.plan.cases) if planner_result is not None else []
        self._progress_reporter.append_event(
            "change_verification_cases_ready",
            "change verification cases prepared",
            build_change_verification_cases_ready_payload(
                manual_case_count=len(request.provided_cases),
                review_required_case_count=len(review_contract.required_cases) if review_contract else 0,
                planner_case_count=len(planner_cases),
                review_hint_enabled=review_contract is not None,
            ),
        )
        plan = self._build_runtime_plan(
            app_id=request.app_id,
            change_summary=request.change_summary,
            manual_cases=manual_cases,
            planner_cases=planner_cases,
            acceptance_criteria=list(request.acceptance_criteria),
        )
        plan_result = self._save_plan(
            plan,
            assets_root=request.assets_root,
            planning_usage=planner_result.planning_usage if planner_result is not None else None,
        )
        self._progress_reporter.append_event(
            "change_verification_plan_saved",
            "change verification plan saved",
            build_change_verification_plan_saved_payload(
                app_id=request.app_id,
                plan_id=plan.plan_id,
                case_count=len(plan.cases),
                plan_path=str(plan_result.plan_path),
                snapshot_path=str(plan_result.snapshot_path),
                planning_usage=plan_result.planning_usage,
            ),
        )
        return plan, plan_result, upstream_review, plan_result.planning_usage

    def _generate_planner_cases(self, request: ChangeVerificationRequest) -> PlanGenerationResult:
        return self._plan_service.generate_change_plan(
            request.to_change_plan_input(),
            resolved_config=self._resolved_config,
            cancel_checker=self._progress_reporter.should_cancel,
            progress_callback=self._progress_reporter.append_event,
        )

    def _build_runtime_plan(
        self,
        *,
        app_id: str,
        change_summary: str | None,
        manual_cases: list[TestCase],
        planner_cases: list[TestCase],
        acceptance_criteria: list[str],
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
            acceptance_criteria=list(acceptance_criteria),
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
