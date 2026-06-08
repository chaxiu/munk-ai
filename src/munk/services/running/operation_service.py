from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any, cast

from munk.config import ResolvedConfig
from munk.execution.models import CaseExecutionRequest, PlanExecutionRequest
from munk.judging import JudgeOptimizationTrigger, JudgeResult
from munk.services.errors import OperationCancelledError
from munk.services.events import RunEventSink
from munk.services.machine_contracts import verdict_exit_code
from munk.services.operations.command_helpers import merged_tracker_artifacts, verdict_from_execution_status
from munk.services.operations.query_service import OperationQueryService
from munk.services.operations.service import OperationCommandResult, OperationService, OperationTracker
from munk.services.operations.submission_service import OperationSubmissionService
from munk.services.plan_execution_service import (
    PlanCaseExecutionOutcome,
    PlanExecutionService,
    SupportsPlanOperationRecord,
)
from munk.services.running.service import RunService
from munk.telemetry import build_telemetry_service
from munk.token_usage import TokenUsage


class RunOperationService:
    def __init__(
        self,
        *,
        plan_execution_service_factory: Callable[
            [ResolvedConfig, OperationTracker, RunEventSink | None], PlanExecutionService
        ]
        | None = None,
    ) -> None:
        self._plan_execution_service_factory = plan_execution_service_factory or self._default_plan_execution_service

    def execute_case(
        self,
        *,
        tracker: OperationTracker,
        request: PlanExecutionRequest,
        case_id: str,
        resolved_config: ResolvedConfig,
        event_sink: RunEventSink | None,
    ) -> OperationCommandResult:
        result = self._plan_execution_service_factory(resolved_config, tracker, event_sink).execute_case_from_plan(
            request,
            case_id=case_id,
        )
        if not tracker.cancel_observed:
            self._run_case_completion_hooks(
                parent_tracker=tracker,
                request=request,
                result=result,
            )
        data = result.model_dump(mode="json")
        return OperationCommandResult(
            data=data,
            artifacts=dict(result.artifacts),
            verification_verdict=None if tracker.cancel_observed else result.verdict,
            result_json=data,
            status="cancelled" if tracker.cancel_observed else "succeeded",
            exit_code=verdict_exit_code(result.verdict),
        )

    def _run_case_completion_hooks(
        self,
        *,
        parent_tracker: OperationTracker,
        request: PlanExecutionRequest,
        result,
    ) -> None:  # noqa: ANN001
        self._run_optimize_child_if_needed(
            parent_tracker=parent_tracker,
            request=request,
            result=result,
        )
        self._run_knowledge_post_action_if_needed(
            parent_tracker=parent_tracker,
            request=request,
            result=result,
        )

    def _run_optimize_child_if_needed(
        self,
        *,
        parent_tracker: OperationTracker,
        request: PlanExecutionRequest,
        result,
    ) -> None:  # noqa: ANN001
        candidate = self._build_optimization_trigger_candidate(result)
        policy_class = cast(Any, import_module("munk.services.optimization.policy").OptimizeCasePolicy)
        request_model = cast(Any, import_module("munk.services.optimization.request_models").OptimizeCaseOperationRequest)
        policy = policy_class()
        if candidate is None or not policy.should_trigger(result=result, candidate=candidate):
            return
        optimize_request = request_model(
            app_id=request.app_id,
            plan_id=request.plan_id,
            case_id=result.case_id,
            case_title=result.summary,
            run_dir=result.run_dir,
            result_path=Path(result.artifacts["result"]),
            trigger=candidate,
            judge_result_path=Path(candidate.judge_result_path) if candidate.judge_result_path else None,
            parent_operation_id=parent_tracker.operation_id,
        )
        request_dir = result.run_dir / "optimize"
        request_dir.mkdir(parents=True, exist_ok=True)
        request_path = request_dir / "operation_request.json"
        request_path.write_text(optimize_request.model_dump_json(indent=2), encoding="utf-8")
        operation_service = OperationService(parent_tracker.registry)
        submission_service = OperationSubmissionService(
            operation_service=operation_service,
            query_service=OperationQueryService(operation_service=operation_service),
            telemetry=build_telemetry_service(workspace_root=Path.cwd()),
            entrypoint="cli",
        )
        response = submission_service.submit(
            kind="optimize_case",
            command="optimize_case",
            request_json=optimize_request.model_dump(mode="json"),
            app_id=request.app_id,
            plan_id=request.plan_id,
            case_id=result.case_id,
            requires_device=False,
            device_ref=None,
            wait=False,
            detach=True,
            detached_argv=[
                "optimize-case",
                "--request-file",
                str(request_path),
                "--json",
                "--detach",
            ],
            parent_operation_id=parent_tracker.operation_id,
            reuse_current_tracker=False,
            execute=lambda tracker: (_ for _ in ()).throw(RuntimeError("optimize_case detached execution required")),
        )
        if response.payload["ok"] is False:
            parent_tracker.append_event(
                event_type="optimize_case_submission_failed",
                message="case optimize child operation submission failed",
                data={
                    "case_id": result.case_id,
                    "error": response.payload["error"]["message"],
                },
            )
            return
        operation_id = str(response.payload["data"]["operation_id"])
        parent_tracker.append_event(
            event_type="optimize_case_submitted",
            message="case optimize child operation submitted",
            data={
                "operation_id": operation_id,
                "case_id": result.case_id,
                "optimization_fields": list(candidate.trigger.optimization_fields),
                "trigger_source": candidate.trigger_source,
                "trigger_signals": list(candidate.trigger_signals),
                "request_path": str(request_path),
            },
        )

    def _run_knowledge_post_action_if_needed(
        self,
        *,
        parent_tracker: OperationTracker,
        request: PlanExecutionRequest,
        result,
    ) -> None:  # noqa: ANN001
        knowledge_request = self._build_knowledge_post_action_request_candidate(request=request, result=result)
        if knowledge_request is None:
            return
        request_dir = result.run_dir / "knowledge"
        request_dir.mkdir(parents=True, exist_ok=True)
        request_path = request_dir / "operation_request.json"
        request_path.write_text(knowledge_request.model_dump_json(indent=2), encoding="utf-8")
        operation_service = OperationService(parent_tracker.registry)
        submission_service = OperationSubmissionService(
            operation_service=operation_service,
            query_service=OperationQueryService(operation_service=operation_service),
            telemetry=build_telemetry_service(workspace_root=Path.cwd()),
            entrypoint="cli",
        )
        knowledge_service_class = cast(Any, import_module("munk.services.knowledge.post_action_service").KnowledgePostActionService)
        knowledge_service = knowledge_service_class()
        response = submission_service.submit(
            kind="knowledge_post_action",
            command="knowledge_post_action",
            request_json=knowledge_request.model_dump(mode="json"),
            app_id=request.app_id,
            plan_id=request.plan_id,
            case_id=result.case_id,
            requires_device=False,
            device_ref=None,
            wait=True,
            detach=False,
            detached_argv=None,
            parent_operation_id=parent_tracker.operation_id,
            reuse_current_tracker=False,
            execute=lambda tracker: knowledge_service.execute_command(
                tracker=tracker,
                request=knowledge_request,
            ),
        )
        if response.payload["ok"] is False:
            parent_tracker.append_event(
                event_type="knowledge_post_action_failed",
                message="knowledge post action execution failed",
                data={
                    "case_id": result.case_id,
                    "error": response.payload["error"]["message"],
                },
            )
            return
        data = response.payload["data"]
        parent_tracker.append_event(
            event_type="knowledge_post_action_completed",
            message="knowledge post action completed",
            data={
                "operation_id": data["operation_id"],
                "case_id": result.case_id,
                "submitted": data.get("submitted", False),
                "candidate_id": data.get("candidate_id"),
                "skip_reason": data.get("skip_reason"),
                "request_path": str(request_path),
            },
        )

    @staticmethod
    def _load_optimization_trigger(judge_result_path: str | None) -> JudgeOptimizationTrigger | None:
        if not judge_result_path:
            return None
        payload = json.loads(Path(judge_result_path).read_text(encoding="utf-8"))
        return RunOperationService._build_trigger_from_judge_payload(payload)

    @staticmethod
    def _build_trigger_from_judge_payload(payload: object) -> JudgeOptimizationTrigger | None:
        if not isinstance(payload, dict):
            return None
        judge_result = JudgeResult.model_validate(payload)
        return JudgeOptimizationTrigger(
            needs_optimization=judge_result.needs_optimization,
            optimization_fields=list(judge_result.optimization_fields),
            optimization_reason=judge_result.optimization_reason,
            optimization_confidence=judge_result.optimization_confidence,
        )

    @staticmethod
    def _load_json_artifact(path_value: str | None) -> object | None:
        if not path_value:
            return None
        path = Path(path_value)
        if not path.exists() or not path.is_file():
            return None
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    @classmethod
    def _build_optimization_trigger_candidate(cls, result) -> Any | None:  # noqa: ANN001
        request_models = cast(Any, import_module("munk.services.optimization.request_models"))
        candidate_class = cast(Any, request_models.OptimizeTriggerCandidate)
        orchestration_payload = cls._load_json_artifact(result.artifacts.get("orchestration_result"))
        attempt_payloads = (
            orchestration_payload.get("attempts", [])
            if isinstance(orchestration_payload, dict)
            else []
        )
        explicit_trigger_index: int | None = None
        explicit_trigger: JudgeOptimizationTrigger | None = None
        explicit_judge_result_path: str | None = None
        for attempt_payload in attempt_payloads:
            if not isinstance(attempt_payload, dict):
                continue
            judge_payload = attempt_payload.get("judge")
            if not isinstance(judge_payload, dict):
                continue
            trigger_payload = judge_payload.get("optimization_trigger")
            trigger = cls._build_trigger_from_payload(trigger_payload)
            if trigger is None or not trigger.needs_optimization:
                continue
            attempt_index = attempt_payload.get("attempt_index")
            if not isinstance(attempt_index, int):
                continue
            explicit_trigger_index = attempt_index
            explicit_trigger = trigger
            judge_artifacts = judge_payload.get("artifacts")
            if isinstance(judge_artifacts, dict):
                raw_path = judge_artifacts.get("judge_result")
                if isinstance(raw_path, str) and raw_path.strip():
                    explicit_judge_result_path = raw_path
            break

        trigger_signals: list[str] = []
        if result.verdict in {"failed", "inconclusive"} and result.attempt_count > 1:
            trigger_signals.append("retried_terminal_failure")
        retry_handoffs = cls._load_json_artifact(result.artifacts.get("retry_handoffs"))
        if isinstance(retry_handoffs, list) and retry_handoffs:
            trigger_signals.append("retry_handoffs_present")
        if result.execution.error_type == "RunnerProtocolError":
            trigger_signals.append("runner_protocol_error")
        repeated_no_progress = cls._has_repeated_no_progress(result)
        if repeated_no_progress:
            trigger_signals.append("repeated_no_progress")

        source_attempt_index = explicit_trigger_index
        if source_attempt_index is None and result.attempts:
            for attempt in result.attempts:
                if attempt.verdict in {"failed", "inconclusive"}:
                    source_attempt_index = attempt.attempt_index
                    break
            if source_attempt_index is None:
                source_attempt_index = result.attempts[-1].attempt_index

        selected_judge_result_path = explicit_judge_result_path
        if selected_judge_result_path is None and source_attempt_index is not None and 0 <= source_attempt_index < len(result.attempts):
            raw_path = result.attempts[source_attempt_index].artifacts.get("judge_result")
            if raw_path:
                selected_judge_result_path = raw_path
        if selected_judge_result_path is None:
            fallback_path = result.artifacts.get("judge_result")
            if fallback_path:
                selected_judge_result_path = fallback_path

        trigger = explicit_trigger
        if trigger is None and selected_judge_result_path:
            trigger = cls._load_optimization_trigger(selected_judge_result_path)
        if trigger is None:
            trigger = JudgeOptimizationTrigger()

        if not trigger_signals and not trigger.needs_optimization:
            return candidate_class(
                trigger=trigger,
                trigger_source="judge",
                trigger_signals=[],
                source_attempt_index=source_attempt_index,
                judge_result_path=selected_judge_result_path,
            )

        trigger_source = "judge" if trigger.needs_optimization else "execution_heuristics"
        return candidate_class(
            trigger=trigger,
            trigger_source=trigger_source,
            trigger_signals=trigger_signals,
            source_attempt_index=source_attempt_index,
            judge_result_path=selected_judge_result_path,
        )

    @staticmethod
    def _build_knowledge_post_action_request_candidate(request: PlanExecutionRequest, result) -> Any | None:  # noqa: ANN001
        request_model = cast(Any, import_module("munk.services.knowledge.request_models").KnowledgePostActionRequest)
        if getattr(result, "verdict", "passed") == "passed":
            return None
        judge_result_path = result.artifacts.get("judge_result")
        if not judge_result_path:
            return None
        return request_model(
            app_id=request.app_id,
            plan_id=request.plan_id,
            case_id=result.case_id,
            case_title=result.summary,
            assets_root=request.assets_root,
            run_dir=result.run_dir,
            judge_result_path=Path(judge_result_path),
            artifact_paths={
                key: Path(value)
                for key, value in result.artifacts.items()
                if key in {
                    "judge_result",
                    "artifact_manifest",
                    "decision_trace",
                    "attempts",
                    "retry_handoffs",
                    "history",
                    "runner_history",
                }
            },
            parent_operation_id=result.operation_id if hasattr(result, "operation_id") else None,
        )

    @staticmethod
    def _build_trigger_from_payload(payload: object) -> JudgeOptimizationTrigger | None:
        if not isinstance(payload, dict):
            return None
        try:
            return JudgeOptimizationTrigger.model_validate(payload)
        except Exception:
            return None

    @staticmethod
    def _has_repeated_no_progress(result) -> bool:  # noqa: ANN001
        if result.attempt_count <= 1:
            return False
        repeated_markers: dict[str, int] = {}
        for attempt in result.attempts:
            marker_parts = [
                (attempt.retry_reason or "").strip().lower(),
                (attempt.judge_reason or "").strip().lower(),
                (attempt.execution.stop_reason or "").strip().lower(),
                (attempt.execution.error_type or "").strip().lower(),
            ]
            marker = " | ".join(part for part in marker_parts if part)
            if not marker:
                continue
            repeated_markers[marker] = repeated_markers.get(marker, 0) + 1
            if repeated_markers[marker] >= 2:
                return True
        return False

    def execute_plan(
        self,
        *,
        tracker: OperationTracker,
        request: PlanExecutionRequest,
        resolved_config: ResolvedConfig,
        event_sink: RunEventSink | None,
    ) -> OperationCommandResult:
        plan_service = self._plan_execution_service_factory(resolved_config, tracker, event_sink)
        result = plan_service.execute_plan_with_case_executor(
            request,
            case_executor=lambda case_request, position_index, total_cases: self._execute_plan_child_case(
                parent_tracker=tracker,
                request=request,
                case_request=case_request,
                position_index=position_index,
                total_cases=total_cases,
                resolved_config=resolved_config,
                event_sink=event_sink,
            ),
        )
        data: dict[str, Any] = {
            "plan_id": result.plan_id,
            "verification_status": result.status,
            "total_cases": result.total_cases,
            "passed_cases": result.passed_cases,
            "failed_cases": result.failed_cases,
            "inconclusive_cases": result.inconclusive_cases,
            "stopped_early": result.stopped_early,
            "summary_path": str(result.summary_path),
            "report_path": str(result.report_path),
            "items": [item.model_dump(mode="json") for item in result.items],
            "token_usage": result.token_usage.model_dump(mode="json") if result.token_usage is not None else None,
        }
        verdict = verdict_from_execution_status(result.status)
        artifacts = {
            "summary": str(result.summary_path),
            "report": str(result.report_path),
            "plan": str(result.summary_path.parent / "plan.json"),
        }
        return OperationCommandResult(
            data=data,
            artifacts=artifacts,
            verification_verdict=None if tracker.cancel_observed else verdict,
            result_json={**data, "artifacts": artifacts},
            status="cancelled" if tracker.cancel_observed else "succeeded",
            exit_code=verdict_exit_code(verdict),
        )

    def _execute_plan_child_case(
        self,
        *,
        parent_tracker: OperationTracker,
        request: PlanExecutionRequest,
        case_request: CaseExecutionRequest,
        position_index: int,
        total_cases: int,
        resolved_config: ResolvedConfig,
        event_sink: RunEventSink | None,
    ) -> PlanCaseExecutionOutcome:
        operation_service = OperationService(parent_tracker.registry)
        case_id = case_request.case.case_id
        title = case_request.case.title or case_id
        child_tracker = operation_service.create_operation(
            kind="run_case",
            request_json={
                **request.model_dump(mode="json"),
                "case_id": case_id,
                "case_title": title,
                "batch_kind": "single_plan_multi_case",
            },
            app_id=request.app_id,
            plan_id=request.plan_id,
            case_id=case_id,
            parent_operation_id=parent_tracker.operation_id,
            batch_id=parent_tracker.operation_id,
            position_index=position_index,
            position_label=f"{position_index}/{total_cases}",
            requires_device=False,
            device_ref=request.device_ref,
        )
        position_label = child_tracker.get_record().position_label
        child_tracker.mark_running(
            pid=parent_tracker.get_record().pid or child_tracker.get_record().pid or 0,
            progress={
                "phase": "running",
                "parent_operation_id": parent_tracker.operation_id,
                "position_label": position_label,
                "case_id": case_id,
                "case_title": title,
            },
        )
        child_tracker.append_event(
            event_type="operation_started",
            message="child case operation started",
            data={
                "parent_operation_id": parent_tracker.operation_id,
                "case_id": case_id,
                "case_title": title,
                "position_label": position_label,
            },
        )
        parent_tracker.update_progress(
            current_child_operation_id=child_tracker.operation_id,
            current_child_case_id=case_id,
            current_child_title=title,
        )
        parent_tracker.append_event(
            event_type="batch_child_started",
            message="plan child case started",
            data={
                "operation_id": child_tracker.operation_id,
                "case_id": case_id,
                "title": title,
                "position_label": position_label,
            },
        )
        child_plan_service = self._plan_execution_service_factory(resolved_config, child_tracker, event_sink)
        try:
            case_result = child_plan_service.execute_case_from_plan(request, case_id=case_id)
        except Exception as exc:
            if isinstance(exc, OperationCancelledError):
                child_tracker.mark_cancelled(
                    progress={
                        "phase": "cancelled",
                        "parent_operation_id": parent_tracker.operation_id,
                        "position_label": position_label,
                        "case_id": case_id,
                        "case_title": title,
                    }
                )
                parent_tracker.append_event(
                    event_type="batch_child_finished",
                    message="plan child case cancelled",
                    data=self._child_case_summary(child_tracker, title=title),
                )
                raise
            child_tracker.mark_failed(
                error_code="runtime_error",
                error_message=str(exc),
                progress={
                    "phase": "failed",
                    "parent_operation_id": parent_tracker.operation_id,
                    "position_label": position_label,
                    "case_id": case_id,
                    "case_title": title,
                },
            )
            parent_tracker.append_event(
                event_type="batch_child_finished",
                message="plan child case failed",
                data=self._child_case_summary(child_tracker, title=title),
            )
            raise

        result_data: dict[str, Any] = case_result.model_dump(mode="json")
        result_json = result_data
        merged_artifacts = merged_tracker_artifacts(child_tracker, case_result.artifacts)
        child_status = "cancelled" if child_tracker.cancel_observed else "succeeded"
        if child_status == "cancelled":
            child_tracker.mark_cancelled(
                result_json=result_json,
                artifacts=merged_artifacts,
                progress={
                    "phase": "cancelled",
                    "parent_operation_id": parent_tracker.operation_id,
                    "position_label": position_label,
                    "case_id": case_id,
                    "case_title": title,
                },
            )
        else:
            child_tracker.mark_succeeded(
                verification_verdict=case_result.verdict,
                result_json=result_json,
                artifacts=merged_artifacts,
                progress={
                    "phase": "completed",
                    "parent_operation_id": parent_tracker.operation_id,
                    "position_label": position_label,
                    "verification_verdict": case_result.verdict,
                    "case_id": case_id,
                    "case_title": title,
                },
            )
            self._run_case_completion_hooks(
                parent_tracker=child_tracker,
                request=request,
                result=case_result,
            )
        parent_tracker.update_progress(
            current_child_operation_id=None,
            current_child_case_id=None,
            current_child_title=None,
            last_child_operation_id=child_tracker.operation_id,
            last_child_case_id=case_id,
            last_child_title=title,
        )
        parent_tracker.append_event(
            event_type="batch_child_finished",
            message="plan child case finished",
            data=self._child_case_summary(child_tracker, title=title),
        )
        return PlanCaseExecutionOutcome(
            result=case_result,
            operation_id=child_tracker.operation_id,
            status=child_status,
        )

    @staticmethod
    def _child_case_summary(child_tracker: OperationTracker, *, title: str) -> dict[str, Any]:
        record = child_tracker.get_record()
        return {
            "operation_id": record.operation_id,
            "plan_id": record.plan_id,
            "case_id": record.case_id,
            "title": title,
            "status": record.status,
            "verification_verdict": record.verification_verdict,
            "position_index": record.position_index,
            "position_label": record.position_label,
            "created_at": record.created_at,
            "started_at": record.started_at,
            "finished_at": record.finished_at,
            "error_code": record.error_code,
            "error_message": record.error_message,
            "token_usage": _token_usage_dict_from_result_json(record.result_json),
        }

    @staticmethod
    def _default_plan_execution_service(
        resolved_config: ResolvedConfig,
        tracker: OperationTracker,
        event_sink: RunEventSink | None,
    ) -> PlanExecutionService:
        return PlanExecutionService(
            resolved_config=resolved_config,
            run_service_factory=lambda: RunService(
                resolved_config=resolved_config,
                event_sink=event_sink,
                operation_tracker=tracker,
            ),
            operation_tracker=_PlanOperationTrackerAdapter(tracker),
        )


def _token_usage_dict_from_result_json(result_json: object) -> dict[str, Any] | None:
    if not isinstance(result_json, dict):
        return None
    raw = result_json.get("token_usage")
    if not isinstance(raw, dict):
        return None
    try:
        usage = TokenUsage.model_validate(raw)
    except Exception:
        return None
    return usage.model_dump(mode="json")


class _PlanOperationTrackerAdapter:
    def __init__(self, tracker: OperationTracker) -> None:
        self._tracker = tracker

    def should_cancel(self) -> bool:
        return self._tracker.should_cancel()

    def raise_if_cancelled(self) -> None:
        self._tracker.raise_if_cancelled()

    def update_artifacts(self, artifacts: dict[str, str]) -> None:
        self._tracker.update_artifacts(artifacts)

    def update_progress(self, **progress: object) -> None:
        self._tracker.update_progress(**progress)

    def get_record(self) -> SupportsPlanOperationRecord:
        record = self._tracker.get_record()
        return _PlanOperationRecordView(
            operation_id=record.operation_id,
            kind=record.kind,
        )


@dataclass
class _PlanOperationRecordView:
    operation_id: str
    kind: str | None
