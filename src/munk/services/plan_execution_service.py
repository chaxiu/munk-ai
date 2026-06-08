from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

from munk.config import ResolvedConfig
from munk.execution.models import (
    CaseExecutionRequest,
    CaseExecutionResult,
    JudgeVerdict,
    PlanCaseExecutionItem,
    PlanExecutionRequest,
    PlanExecutionResult,
)
from munk.planning.models import RequirementPlan
from munk.planning.storage import CoreCaseRegistry, PlanStore
from munk.reporting.service import PlanReportService
from munk.runtime import build_case_request
from munk.runtime_defaults import (
    DEFAULT_ICON_CONF,
    DEFAULT_INTERVAL,
    DEFAULT_MAX_SECONDS,
    DEFAULT_MAX_SIDE,
    DEFAULT_MAX_STEPS,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    DEFAULT_VL_MAX_SIDE,
)
from munk.services.artifact_manifest_models import ReproductionTargetKind
from munk.services.artifact_manifest_service import ArtifactManifestService
from munk.services.errors import CaseNotFoundError, PlanNotFoundError
from munk.services.running.paths import create_unique_run_dir
from munk.services.running.service import RunService
from munk.testing import TestCase
from munk.token_usage import merge_token_usages


class SupportsPlanOperationRecord(Protocol):
    @property
    def operation_id(self) -> str: ...

    @property
    def kind(self) -> str | None: ...


class SupportsPlanOperationTracker(Protocol):
    def should_cancel(self) -> bool: ...

    def raise_if_cancelled(self) -> None: ...

    def update_artifacts(self, artifacts: dict[str, str]) -> object | None: ...

    def update_progress(self, **progress: object) -> object | None: ...

    def get_record(self) -> SupportsPlanOperationRecord: ...


@dataclass(frozen=True)
class PlanCaseExecutionOutcome:
    result: CaseExecutionResult
    operation_id: str | None = None
    status: str | None = None


class PlanExecutionService:
    def __init__(
        self,
        *,
        resolved_config: ResolvedConfig,
        plan_store: PlanStore | None = None,
        core_case_registry: CoreCaseRegistry | None = None,
        run_service_factory: Callable[[], RunService] | None = None,
        report_service: PlanReportService | None = None,
        operation_tracker: SupportsPlanOperationTracker | None = None,
    ) -> None:
        self._resolved_config = resolved_config
        self._plan_store = plan_store or PlanStore()
        self._core_case_registry = core_case_registry or CoreCaseRegistry(self._plan_store.root_dir)
        self._run_service_factory = run_service_factory or (lambda: RunService(resolved_config=self._resolved_config))
        self._report_service = report_service or PlanReportService()
        self._operation_tracker = operation_tracker
        self._artifact_manifest_service = ArtifactManifestService()

    def execute_case_from_plan(
        self,
        request: PlanExecutionRequest,
        *,
        case_id: str,
    ) -> CaseExecutionResult:
        plan = self._load_plan(request)
        case = self._find_case(plan, case_id=case_id)
        case_request = self._build_case_request(request, case)
        return self._run_service_factory().execute_case(case_request)

    def execute_plan(self, request: PlanExecutionRequest) -> PlanExecutionResult:
        plan = self._load_plan(request)
        return self.execute_plan_model(plan, request)

    def execute_plan_with_case_executor(
        self,
        request: PlanExecutionRequest,
        *,
        case_executor: Callable[[CaseExecutionRequest, int, int], PlanCaseExecutionOutcome],
    ) -> PlanExecutionResult:
        plan = self._load_plan(request)
        return self.execute_plan_model(plan, request, case_executor=case_executor)

    def execute_plan_model(
        self,
        plan: RequirementPlan,
        request: PlanExecutionRequest,
        *,
        case_executor: Callable[[CaseExecutionRequest, int, int], PlanCaseExecutionOutcome] | None = None,
    ) -> PlanExecutionResult:
        self._raise_if_cancelled()
        plan_run_dir = self._prepare_plan_run_dir()
        self._write_plan_copy(plan_run_dir, plan)
        self._update_operation_artifacts(
            {
                "plan_run_dir": str(plan_run_dir),
                "plan": str(plan_run_dir / "plan.json"),
                "artifact_manifest": str(plan_run_dir / "artifact_manifest.json"),
            }
        )
        self._update_operation_progress(total_cases=len(plan.cases), completed_cases=0)

        items: list[PlanCaseExecutionItem] = []
        case_results: list[CaseExecutionResult] = []
        case_operation_ids: dict[str, str | None] = {}
        stopped_early = False

        for position_index, case in enumerate(plan.cases, start=1):
            if self._should_cancel():
                stopped_early = True
                break
            self._update_operation_progress(current_case_id=case.case_id, completed_cases=len(items))
            case_request = self._build_case_request(request, case)
            outcome = (case_executor or self._default_case_executor)(
                case_request,
                position_index,
                len(plan.cases),
            )
            result = outcome.result
            if "artifact_manifest" not in result.artifacts:
                raise RuntimeError(
                    f"case run did not produce artifact_manifest: case_id={case.case_id} run_dir={result.run_dir}"
                )
            case_results.append(result)
            case_operation_ids[case.case_id] = outcome.operation_id
            items.append(
                self._build_case_item(
                    case,
                    result,
                    operation_id=outcome.operation_id,
                    status=outcome.status,
                )
            )
            self._update_operation_progress(completed_cases=len(items), last_case_id=case.case_id)
            self._update_operation_artifacts(
                {
                    f"case_{case.case_id}_run_dir": str(result.run_dir),
                    f"case_{case.case_id}_result": result.artifacts.get("result", ""),
                    f"case_{case.case_id}_artifact_manifest": result.artifacts.get(
                        "artifact_manifest", ""
                    ),
                    f"case_{case.case_id}_operation_id": outcome.operation_id or "",
                }
            )

            if request.fail_fast and result.verdict == "failed":
                stopped_early = True
                break

        summary_path = plan_run_dir / "plan_execution.json"
        report_path = plan_run_dir / "report.json"
        plan_result = self._build_plan_result(
            request=request,
            total_cases=len(plan.cases),
            items=items,
            stopped_early=stopped_early,
            summary_path=summary_path,
            report_path=report_path,
        )
        self._write_plan_result(summary_path, plan_result)
        self._update_operation_artifacts({"summary": str(summary_path), "report": str(report_path)})
        report = self._report_service.build_report(
            plan=plan,
            plan_result=plan_result,
            case_results=case_results,
            report_path=report_path,
        )
        self._report_service.write_report(report_path, report)
        manifest_path = plan_run_dir / "artifact_manifest.json"
        plan_artifacts = {
            "plan": str(plan_run_dir / "plan.json"),
            "summary": str(summary_path),
            "report": str(report_path),
            "artifact_manifest": str(manifest_path),
        }
        plan_manifest = self._artifact_manifest_service.build_plan_manifest(
            root_dir=plan_run_dir,
            artifacts=plan_artifacts,
            case_results=case_results,
            case_operation_ids=case_operation_ids,
            case_titles={case.case_id: case.title for case in plan.cases},
            operation_id=self._operation_id(),
            operation_kind=self._operation_kind(),
            verification_verdict=self._verification_verdict_for_status(plan_result.status),
        )
        self._artifact_manifest_service.write_manifest(manifest_path, plan_manifest)
        self._update_operation_artifacts(plan_artifacts)
        return plan_result

    def _build_case_request(
        self,
        request: PlanExecutionRequest,
        case: TestCase,
    ):
        return build_case_request(
            plan_id=request.plan_id,
            app_id=request.app_id,
            case=case,
            app_target=request.app_target,
            device_ref=request.device_ref,
            artifact_path=request.artifact_path,
            assets_root=request.assets_root,
            max_steps=self._resolve_budget_int(case, request, "max_steps", DEFAULT_MAX_STEPS),
            max_seconds=self._resolve_budget_float(case, request, "max_seconds", DEFAULT_MAX_SECONDS),
            interval=self._require_float_override(request, "interval", DEFAULT_INTERVAL),
            max_side=self._require_int_override(request, "max_side", DEFAULT_MAX_SIDE),
            icon_conf=self._require_float_override(request, "icon_conf", DEFAULT_ICON_CONF),
            max_tokens=self._require_int_override(request, "max_tokens", DEFAULT_MAX_TOKENS),
            temperature=self._require_float_override(request, "temperature", DEFAULT_TEMPERATURE),
            vl_max_side=self._require_int_override(request, "vl_max_side", DEFAULT_VL_MAX_SIDE),
        )

    def _load_plan(self, request: PlanExecutionRequest) -> RequirementPlan:
        plan_store, core_case_registry = self._storage_for_assets_root(request.assets_root)
        try:
            plan = plan_store.load(request.app_id, request.plan_id)
        except FileNotFoundError as exc:
            raise PlanNotFoundError(str(exc)) from exc
        updated_cases = core_case_registry.apply_to_cases(request.app_id, list(plan.cases))
        if updated_cases == plan.cases:
            return plan
        return plan.model_copy(update={"cases": updated_cases})

    def _storage_for_assets_root(self, assets_root: Path | None) -> tuple[PlanStore, CoreCaseRegistry]:
        if assets_root is None:
            return self._plan_store, self._core_case_registry
        plan_store = PlanStore(assets_root)
        return plan_store, CoreCaseRegistry(plan_store.root_dir)

    @staticmethod
    def _find_case(plan: RequirementPlan, *, case_id: str) -> TestCase:
        for case in plan.cases:
            if case.case_id == case_id:
                return case
        raise CaseNotFoundError(f"case not found in plan '{plan.plan_id}': {case_id}")

    @staticmethod
    def _prepare_plan_run_dir() -> Path:
        return create_unique_run_dir(prefix="plan_run")

    @staticmethod
    def _write_plan_copy(plan_run_dir: Path, plan: RequirementPlan) -> None:
        plan_path = plan_run_dir / "plan.json"
        with plan_path.open("w", encoding="utf-8") as f:
            f.write(plan.model_dump_json(indent=2))

    @staticmethod
    def _build_case_item(
        case: TestCase,
        result: CaseExecutionResult,
        *,
        operation_id: str | None = None,
        status: str | None = None,
    ) -> PlanCaseExecutionItem:
        return PlanCaseExecutionItem(
            case_id=case.case_id,
            title=case.title,
            operation_id=operation_id,
            status=status,
            verdict=result.verdict,
            execution_status=result.execution.status,
            judge_summary=result.summary,
            stop_reason=result.execution.stop_reason,
            run_dir=result.run_dir,
            error_message=result.execution.error_message,
            token_usage=result.token_usage,
        )

    def _default_case_executor(
        self,
        case_request: CaseExecutionRequest,
        _position_index: int,
        _total_cases: int,
    ) -> PlanCaseExecutionOutcome:
        return PlanCaseExecutionOutcome(result=self._run_service_factory().execute_case(case_request))

    @staticmethod
    def _build_plan_result(
        *,
        request: PlanExecutionRequest,
        total_cases: int,
        items: list[PlanCaseExecutionItem],
        stopped_early: bool,
        summary_path: Path,
        report_path: Path,
    ) -> PlanExecutionResult:
        passed_cases = sum(1 for item in items if item.verdict == "passed")
        failed_cases = sum(1 for item in items if item.verdict == "failed")
        inconclusive_cases = sum(1 for item in items if item.verdict == "inconclusive")
        if stopped_early:
            status = "stopped"
        elif failed_cases:
            status = "failed"
        elif inconclusive_cases:
            status = "inconclusive"
        else:
            status = "passed"
        return PlanExecutionResult(
            app_id=request.app_id,
            plan_id=request.plan_id,
            status=status,
            total_cases=total_cases,
            passed_cases=passed_cases,
            failed_cases=failed_cases,
            inconclusive_cases=inconclusive_cases,
            stopped_early=stopped_early,
            items=items,
            summary_path=summary_path,
            report_path=report_path,
            token_usage=merge_token_usages(item.token_usage for item in items),
        )

    @staticmethod
    def _write_plan_result(summary_path: Path, result: PlanExecutionResult) -> None:
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        with summary_path.open("w", encoding="utf-8") as f:
            json.dump(result.model_dump(mode="json"), f, ensure_ascii=False, indent=2)

    @staticmethod
    def _require_int_override(
        request: PlanExecutionRequest,
        key: str,
        default: int,
    ) -> int:
        value = request.runtime_overrides.get(key, default)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"runtime override '{key}' must be an integer")
        return value

    @staticmethod
    def _resolve_budget_int(
        case: TestCase,
        request: PlanExecutionRequest,
        key: str,
        default: int,
    ) -> int:
        if key in request.runtime_overrides:
            return PlanExecutionService._require_int_override(request, key, default)
        budget = case.budget
        if budget is None:
            return default
        value = getattr(budget, key)
        return default if value is None else value

    @staticmethod
    def _resolve_budget_float(
        case: TestCase,
        request: PlanExecutionRequest,
        key: str,
        default: float,
    ) -> float:
        if key in request.runtime_overrides:
            return PlanExecutionService._require_float_override(request, key, default)
        budget = case.budget
        if budget is None:
            return default
        value = getattr(budget, key)
        return default if value is None else float(value)

    @staticmethod
    def _require_float_override(
        request: PlanExecutionRequest,
        key: str,
        default: float,
    ) -> float:
        value = request.runtime_overrides.get(key, default)
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError(f"runtime override '{key}' must be a number")
        return float(value)

    def _should_cancel(self) -> bool:
        tracker = self._operation_tracker
        if tracker is None:
            return False
        return tracker.should_cancel()

    def _raise_if_cancelled(self) -> None:
        tracker = self._operation_tracker
        if tracker is not None:
            tracker.raise_if_cancelled()

    def _update_operation_artifacts(self, artifacts: dict[str, str]) -> None:
        tracker = self._operation_tracker
        if tracker is not None:
            tracker.update_artifacts(artifacts)

    def _update_operation_progress(self, **progress: object) -> None:
        tracker = self._operation_tracker
        if tracker is not None:
            tracker.update_progress(**progress)

    def _operation_id(self) -> str | None:
        tracker = self._operation_tracker
        if tracker is None:
            return None
        try:
            return tracker.get_record().operation_id
        except Exception:
            return getattr(tracker, "operation_id", None)

    def _operation_kind(self) -> ReproductionTargetKind | None:
        tracker = self._operation_tracker
        if tracker is None:
            return None
        try:
            kind = tracker.get_record().kind
        except Exception:
            kind = getattr(tracker, "kind", None)
        if kind in {"plan", "run_case", "run_plan", "run_plans", "verify_change", "review"}:
            return cast(ReproductionTargetKind, kind)
        return None

    @staticmethod
    def _verification_verdict_for_status(status: str) -> JudgeVerdict:
        if status == "failed":
            return "failed"
        if status in {"inconclusive", "stopped"}:
            return "inconclusive"
        return "passed"
