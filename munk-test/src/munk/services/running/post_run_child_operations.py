from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any, cast

from munk.artifacts import ARTIFACT_ID_RESULT
from munk.execution.models import CaseExecutionResult, PlanExecutionRequest
from munk.services.operations.command_specs import build_operation_cli_argv
from munk.services.operations.query_service import OperationQueryService
from munk.services.operations.service import OperationService, OperationTracker
from munk.services.operations.submission_service import OperationSubmissionService
from munk.services.post_run_analysis import (
    build_optimize_trigger_candidate,
    resolve_case_run_evidence,
    should_trigger_knowledge_post_action,
)
from munk.services.running.operation_payloads import build_post_run_child_operation_event_payload
from munk.telemetry import build_telemetry_service


def run_case_completion_hooks(
    *,
    parent_tracker: OperationTracker,
    request: PlanExecutionRequest,
    result: CaseExecutionResult,
) -> None:
    _run_optimize_child_if_needed(
        parent_tracker=parent_tracker,
        request=request,
        result=result,
    )
    _run_knowledge_post_action_if_needed(
        parent_tracker=parent_tracker,
        request=request,
        result=result,
    )


def _run_optimize_child_if_needed(
    *,
    parent_tracker: OperationTracker,
    request: PlanExecutionRequest,
    result: CaseExecutionResult,
) -> None:
    candidate = build_optimize_trigger_candidate(result)
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
        result_path=Path(result.artifacts[ARTIFACT_ID_RESULT]),
        trigger=candidate,
        judge_result_path=Path(candidate.judge_result_path) if candidate.judge_result_path else None,
        parent_operation_id=parent_tracker.operation_id,
    )
    request_path = _write_operation_request(
        result_dir=result.run_dir,
        request_name="optimize",
        payload_json=optimize_request.model_dump_json(indent=2),
    )
    response_payload = _submit_detached_child_operation(
        parent_tracker=parent_tracker,
        kind="optimize_case",
        command="optimize_case",
        request_json=optimize_request.model_dump(mode="json"),
        request_path=request_path,
        app_id=request.app_id,
        plan_id=request.plan_id,
        case_id=result.case_id,
    )
    if response_payload["ok"] is False:
        error_payload = cast(dict[str, object], response_payload["error"])
        parent_tracker.append_timeline_event(
            event_type="child_operation_submission_failed",
            message="case optimize child operation submission failed",
            agent_role="optimize",
            timeline_scope="parent_run",
            timeline_phase="failed",
            summary="optimize child operation submission failed",
            attempt_index=candidate.source_attempt_index,
            parent_operation_id=parent_tracker.operation_id,
            app_id=request.app_id,
            plan_id=request.plan_id,
            case_id=result.case_id,
            data=build_post_run_child_operation_event_payload(
                child_kind="optimize_case",
                case_id=result.case_id,
                error=cast(str | None, error_payload.get("message")),
            ),
        )
        return
    data_payload = cast(dict[str, object], response_payload["data"])
    operation_id = str(data_payload["operation_id"])
    parent_tracker.append_timeline_event(
        event_type="child_operation_submitted",
        message="case optimize child operation submitted",
        agent_role="optimize",
        timeline_scope="parent_run",
        timeline_phase="submitted",
        summary="optimize child operation submitted",
        attempt_index=candidate.source_attempt_index,
        parent_operation_id=parent_tracker.operation_id,
        child_operation_id=operation_id,
        app_id=request.app_id,
        plan_id=request.plan_id,
        case_id=result.case_id,
        data=build_post_run_child_operation_event_payload(
            child_kind="optimize_case",
            operation_id=operation_id,
            case_id=result.case_id,
            request_path=str(request_path),
            optimization_fields=list(candidate.trigger.optimization_fields),
            trigger_source=candidate.trigger_source,
            trigger_signals=list(candidate.trigger_signals),
        ),
    )


def _run_knowledge_post_action_if_needed(
    *,
    parent_tracker: OperationTracker,
    request: PlanExecutionRequest,
    result: CaseExecutionResult,
) -> None:
    if not should_trigger_knowledge_post_action(result):
        return
    request_model = cast(
        Any,
        import_module("munk.services.knowledge.request_models").KnowledgePostActionOperationRequest,
    )
    evidence = resolve_case_run_evidence(result, prefer_optimization_attempt=False)
    resolve_effective_assets_root = import_module(
        "munk.services.knowledge.loader"
    ).resolve_effective_assets_root
    knowledge_request = request_model(
        app_id=request.app_id,
        plan_id=request.plan_id,
        case_id=result.case_id,
        case_title=result.summary,
        run_dir=result.run_dir,
        result_path=Path(result.artifacts[ARTIFACT_ID_RESULT]),
        assets_root=resolve_effective_assets_root(request.assets_root),
        judge_result_path=evidence.judge_result_path,
        source_attempt_index=evidence.source_attempt_index,
        parent_operation_id=parent_tracker.operation_id,
    )
    request_path = _write_operation_request(
        result_dir=result.run_dir,
        request_name="knowledge",
        payload_json=knowledge_request.model_dump_json(indent=2),
    )
    response_payload = _submit_detached_child_operation(
        parent_tracker=parent_tracker,
        kind="knowledge_post_action",
        command="knowledge_post_action",
        request_json=knowledge_request.model_dump(mode="json"),
        request_path=request_path,
        app_id=request.app_id,
        plan_id=request.plan_id,
        case_id=result.case_id,
    )
    if response_payload["ok"] is False:
        error_payload = cast(dict[str, object], response_payload["error"])
        parent_tracker.append_timeline_event(
            event_type="child_operation_submission_failed",
            message="knowledge post action child operation submission failed",
            agent_role="knowledge",
            timeline_scope="parent_run",
            timeline_phase="failed",
            summary="knowledge child operation submission failed",
            attempt_index=evidence.source_attempt_index,
            parent_operation_id=parent_tracker.operation_id,
            app_id=request.app_id,
            plan_id=request.plan_id,
            case_id=result.case_id,
            data=build_post_run_child_operation_event_payload(
                child_kind="knowledge_post_action",
                case_id=result.case_id,
                error=cast(str | None, error_payload.get("message")),
            ),
        )
        return
    data_payload = cast(dict[str, object], response_payload["data"])
    operation_id = str(data_payload["operation_id"])
    parent_tracker.append_timeline_event(
        event_type="child_operation_submitted",
        message="knowledge post action child operation submitted",
        agent_role="knowledge",
        timeline_scope="parent_run",
        timeline_phase="submitted",
        summary="knowledge child operation submitted",
        attempt_index=evidence.source_attempt_index,
        parent_operation_id=parent_tracker.operation_id,
        child_operation_id=operation_id,
        app_id=request.app_id,
        plan_id=request.plan_id,
        case_id=result.case_id,
        data=build_post_run_child_operation_event_payload(
            child_kind="knowledge_post_action",
            operation_id=operation_id,
            case_id=result.case_id,
            request_path=str(request_path),
            source_attempt_index=evidence.source_attempt_index,
            judge_result_path=(str(evidence.judge_result_path) if evidence.judge_result_path else None),
        ),
    )


def _write_operation_request(*, result_dir: Path, request_name: str, payload_json: str) -> Path:
    request_dir = result_dir / request_name
    request_dir.mkdir(parents=True, exist_ok=True)
    request_path = request_dir / "operation_request.json"
    request_path.write_text(payload_json, encoding="utf-8")
    return request_path


def _submit_detached_child_operation(
    *,
    parent_tracker: OperationTracker,
    kind: str,
    command: str,
    request_json: dict[str, Any],
    request_path: Path,
    app_id: str,
    plan_id: str,
    case_id: str,
) -> dict[str, object]:
    operation_service = OperationService(parent_tracker.registry)
    submission_service = OperationSubmissionService(
        operation_service=operation_service,
        query_service=OperationQueryService(operation_service=operation_service),
        telemetry=build_telemetry_service(workspace_root=Path.cwd()),
        entrypoint="cli",
    )
    response = submission_service.submit(
        kind=kind,
        command=command,
        request_json=request_json,
        app_id=app_id,
        plan_id=plan_id,
        case_id=case_id,
        requires_device=False,
        device_ref=None,
        wait=False,
        detach=True,
        detached_argv=build_operation_cli_argv(command, request_file=request_path, include_detach=True),
        parent_operation_id=parent_tracker.operation_id,
        reuse_current_tracker=False,
        execute=lambda tracker: (_ for _ in ()).throw(RuntimeError(f"{command} detached execution required")),
    )
    return cast(dict[str, object], response.payload)
