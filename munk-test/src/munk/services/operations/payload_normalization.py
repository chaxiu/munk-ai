from __future__ import annotations

from typing import Any, cast

from pydantic import BaseModel, ValidationError

from munk.execution.models import CaseExecutionResult, ChangeVerificationRequest
from munk.planning.models import RequirementInput
from munk.recording.models import RecordingAnalysisResult
from munk.services.errors import OperationPayloadValidationError
from munk.services.operations.models import OperationKind


def normalize_operation_request_payload(kind: OperationKind, payload: object) -> dict[str, Any]:
    payload_dict = _payload_dict(payload)
    if kind == "plan":
        return _validated_model_dump_or_raise("request", kind, RequirementInput, payload_dict)
    if kind == "run_case":
        from munk.services.running.operation_payloads import RunCaseOperationRequest

        return _validated_model_dump_or_raise("request", kind, RunCaseOperationRequest, payload_dict)
    if kind == "run_plan":
        from munk.services.running.operation_payloads import RunPlanOperationRequest

        return _validated_model_dump_or_raise("request", kind, RunPlanOperationRequest, payload_dict)
    if kind == "run_plans":
        from munk.services.running.operation_payloads import RunPlansOperationRequest

        return _validated_model_dump_or_raise("request", kind, RunPlansOperationRequest, payload_dict)
    if kind == "verify_change":
        return _validated_model_dump_or_raise("request", kind, ChangeVerificationRequest, payload_dict)
    if kind == "review":
        from munk.reviewing.models import ReviewRequest

        return _validated_model_dump_or_raise("request", kind, ReviewRequest, payload_dict)
    if kind == "knowledge_post_action":
        from munk.services.knowledge.request_models import KnowledgePostActionOperationRequest

        return _validated_model_dump_or_raise(
            "request",
            kind,
            KnowledgePostActionOperationRequest,
            payload_dict,
        )
    if kind == "optimize_case":
        from munk.services.optimization.request_models import OptimizeCaseOperationRequest

        return _validated_model_dump_or_raise("request", kind, OptimizeCaseOperationRequest, payload_dict)
    if kind == "record_case":
        from munk.services.recording.operation_payloads import RecordingSessionOperationRequest

        return _validated_model_dump_or_raise(
            "request",
            kind,
            RecordingSessionOperationRequest,
            payload_dict,
        )
    if kind == "recording_analysis":
        from munk.services.recording.operation_payloads import RecordingAnalysisOperationRequest

        return _validated_model_dump_or_raise(
            "request",
            kind,
            RecordingAnalysisOperationRequest,
            payload_dict,
        )
    if kind == "interactive_session":
        from munk.services.interactive.operation_payloads import InteractiveSessionOperationRequest

        return _validated_model_dump_or_raise(
            "request",
            kind,
            InteractiveSessionOperationRequest,
            payload_dict,
        )
    return payload_dict


def normalize_operation_progress_payload(kind: OperationKind, payload: object) -> dict[str, Any]:
    payload_dict = _payload_dict(payload)
    if not payload_dict:
        return payload_dict
    if _is_timeline_only_progress_payload(payload_dict):
        return payload_dict
    if kind == "run_plans":
        from munk.services.running.operation_payloads import RunPlansProgressPayload

        return _validated_subset_model_dump_or_raise("progress", kind, RunPlansProgressPayload, payload_dict)
    if kind == "run_plan":
        from munk.services.running.operation_payloads import (
            RunPlanChildOperationProgressPayload,
            RunPlanProgressPayload,
        )

        model_type = (
            RunPlanChildOperationProgressPayload
            if "parent_operation_id" in payload_dict
            else RunPlanProgressPayload
        )
        return _validated_subset_model_dump_or_raise("progress", kind, model_type, payload_dict)
    if kind == "run_case":
        from munk.services.recording.operation_payloads import RecordingReplayProgress
        from munk.services.running.operation_payloads import (
            RunCaseChildOperationProgressPayload,
            RunCaseOperationProgressPayload,
        )

        if _is_recording_replay_progress_payload(payload_dict):
            return _validated_subset_model_dump_or_raise("progress", kind, RecordingReplayProgress, payload_dict)
        if _is_run_case_child_progress_payload(payload_dict):
            return _validated_subset_model_dump_or_raise(
                "progress",
                kind,
                RunCaseChildOperationProgressPayload,
                payload_dict,
            )
        if _is_run_case_root_progress_payload(payload_dict):
            return _validated_subset_model_dump_or_raise(
                "progress",
                kind,
                RunCaseOperationProgressPayload,
                payload_dict,
            )
        return payload_dict
    if kind == "verify_change":
        from munk.services.verify_change_event_payloads import VerifyChangeOperationProgressPayload

        return _validated_subset_model_dump_or_raise(
            "progress",
            kind,
            VerifyChangeOperationProgressPayload,
            payload_dict,
        )
    if kind == "plan":
        from munk.services.planning.event_payloads import PlanOperationProgressPayload

        return _validated_subset_model_dump_or_raise("progress", kind, PlanOperationProgressPayload, payload_dict)
    if kind == "record_case":
        from munk.services.recording.operation_payloads import RecordingSessionProgress

        return _validated_subset_model_dump_or_raise("progress", kind, RecordingSessionProgress, payload_dict)
    if kind == "recording_analysis":
        from munk.services.recording.operation_payloads import RecordingAnalysisProgress

        return _validated_subset_model_dump_or_raise("progress", kind, RecordingAnalysisProgress, payload_dict)
    if kind == "interactive_session":
        from munk.services.interactive.operation_payloads import InteractiveSessionOperationProgress

        return _validated_subset_model_dump_or_raise(
            "progress",
            kind,
            InteractiveSessionOperationProgress,
            payload_dict,
        )
    return payload_dict


def normalize_operation_result_payload(kind: OperationKind, payload: object | None) -> dict[str, Any] | None:
    if payload is None:
        return None
    payload_dict = _payload_dict(payload)
    if kind == "plan":
        from munk.execution.models import PhasedOperationResult

        return _validated_model_dump_or_raise("result", kind, PhasedOperationResult, payload_dict)
    if kind == "run_case":
        return _validated_model_dump_or_raise("result", kind, CaseExecutionResult, payload_dict)
    if kind == "run_plan":
        from munk.services.running.operation_payloads import RunPlanOperationResultPayload

        return _validated_model_dump_or_raise("result", kind, RunPlanOperationResultPayload, payload_dict)
    if kind == "run_plans":
        from munk.services.running.operation_payloads import RunPlansResultPayload

        return _validated_model_dump_or_raise("result", kind, RunPlansResultPayload, payload_dict)
    if kind == "verify_change":
        from munk.services.verify_change_operation_payloads import VerifyChangeOperationResultPayload

        return _validated_model_dump_or_raise(
            "result",
            kind,
            VerifyChangeOperationResultPayload,
            payload_dict,
        )
    if kind == "review":
        from munk.services.reviewing.operation_payloads import ReviewOperationResultPayload

        return _validated_model_dump_or_raise("result", kind, ReviewOperationResultPayload, payload_dict)
    if kind == "knowledge_post_action":
        from munk.services.knowledge.operation_payloads import KnowledgePostActionOperationResultPayload

        return _validated_model_dump_or_raise(
            "result",
            kind,
            KnowledgePostActionOperationResultPayload,
            payload_dict,
        )
    if kind == "optimize_case":
        from munk.services.optimization.operation_payloads import OptimizeCaseOperationResultPayload

        return _validated_model_dump_or_raise(
            "result",
            kind,
            OptimizeCaseOperationResultPayload,
            payload_dict,
        )
    if kind == "record_case":
        from munk.services.recording.operation_payloads import RecordingSessionTerminalResult

        return _validated_model_dump_or_raise(
            "result",
            kind,
            RecordingSessionTerminalResult,
            payload_dict,
        )
    if kind == "recording_analysis":
        return _validated_model_dump_or_raise("result", kind, RecordingAnalysisResult, payload_dict)
    return payload_dict


def _payload_dict(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TypeError("operation payload must be a dict")
    return cast(dict[str, Any], dict(payload))


def _validated_model_dump(model_type: type[BaseModel], payload: dict[str, Any]) -> dict[str, Any]:
    model = model_type.model_validate(payload)
    return cast(dict[str, Any], model.model_dump(mode="json", exclude_none=True))


def _validated_model_dump_or_raise(
    payload_role: str,
    kind: OperationKind,
    model_type: type[BaseModel],
    payload: dict[str, Any],
) -> dict[str, Any]:
    try:
        return _validated_model_dump(model_type, payload)
    except ValidationError as exc:
        raise _payload_validation_error(
            kind=kind,
            payload_role=payload_role,
            model_type=model_type,
            exc=exc,
        ) from exc


def _validated_subset_model_dump(model_type: type[BaseModel], payload: dict[str, Any]) -> dict[str, Any]:
    model_fields = set(cast(dict[str, object], model_type.model_fields))
    core_payload = {key: value for key, value in payload.items() if key in model_fields}
    extras = {key: value for key, value in payload.items() if key not in model_fields}
    return {**extras, **_validated_model_dump(model_type, core_payload)}


def _validated_subset_model_dump_or_raise(
    payload_role: str,
    kind: OperationKind,
    model_type: type[BaseModel],
    payload: dict[str, Any],
) -> dict[str, Any]:
    try:
        return _validated_subset_model_dump(model_type, payload)
    except ValidationError as exc:
        raise _payload_validation_error(
            kind=kind,
            payload_role=payload_role,
            model_type=model_type,
            exc=exc,
        ) from exc


def _payload_validation_error(
    *,
    kind: OperationKind,
    payload_role: str,
    model_type: type[BaseModel],
    exc: ValidationError,
) -> OperationPayloadValidationError:
    issues = [
        f"{'.'.join(str(item) for item in error['loc'])}: {error['msg']}"
        for error in exc.errors()
    ]
    return OperationPayloadValidationError(
        kind=kind,
        payload_role=payload_role,
        model_name=model_type.__name__,
        issues=issues or [str(exc)],
    )


def _is_timeline_only_progress_payload(payload: dict[str, Any]) -> bool:
    timeline_keys = {
        "last_event_type",
        "agent_role",
        "timeline_scope",
        "timeline_phase",
        "attempt_index",
        "parent_operation_id",
        "child_operation_id",
        "app_id",
        "plan_id",
        "case_id",
        "summary",
        "lifecycle_state",
        "event_timestamp",
        "runner_event_type",
        "detached_pid",
        "background_mode",
    }
    return set(payload).issubset(timeline_keys)


def _is_recording_replay_progress_payload(payload: dict[str, Any]) -> bool:
    return "recording_id" in payload or "source_recording_case_path" in payload


def _is_run_case_child_progress_payload(payload: dict[str, Any]) -> bool:
    child_keys = {"phase", "parent_operation_id", "position_label", "case_title"}
    return bool(set(payload).intersection(child_keys))


def _is_run_case_root_progress_payload(payload: dict[str, Any]) -> bool:
    root_keys = {"orchestration_status", "current_attempt", "retry_count", "runner_event_type"}
    return bool(set(payload).intersection(root_keys))
