from __future__ import annotations

from importlib import import_module
from typing import Any, cast

from pydantic import BaseModel, ValidationError

from munk.services.errors import OperationEventPayloadValidationError

_EVENT_PAYLOAD_MODEL_PATHS: dict[str, tuple[str, str]] = {
    "run_started": ("munk.services.events", "RunStartedEventPayload"),
    "step_started": ("munk.services.events", "StepStartedEventPayload"),
    "perception_completed": ("munk.services.events", "PerceptionCompletedEventPayload"),
    "runner_tool_called": ("munk.services.events", "RunnerToolCalledEventPayload"),
    "runner_contract_miss": ("munk.services.events", "RunnerContractMissEventPayload"),
    "runner_decision_completed": ("munk.services.events", "RunnerDecisionCompletedEventPayload"),
    "action_proposed": ("munk.services.events", "RunnerActionEventPayload"),
    "action_execution_started": ("munk.services.events", "RunnerActionEventPayload"),
    "action_executed": ("munk.services.events", "RunnerActionEventPayload"),
    "action_execution_failed": ("munk.services.events", "RunnerActionEventPayload"),
    "run_stopped": ("munk.services.events", "RunStoppedEventPayload"),
    "run_failed": ("munk.services.events", "RunFailedEventPayload"),
    "log": ("munk.services.events", "LogEventPayload"),
    "agent_started": ("munk.services.operations.lifecycle_event_payloads", "AgentRuntimeLifecycleEventPayload"),
    "agent_ended": ("munk.services.operations.lifecycle_event_payloads", "AgentRuntimeLifecycleEventPayload"),
    "agent_canceled": ("munk.services.operations.lifecycle_event_payloads", "AgentRuntimeLifecycleEventPayload"),
    "agent_completed": ("munk.services.operations.lifecycle_event_payloads", "AgentRuntimeLifecycleEventPayload"),
    "agent_failed": ("munk.services.operations.lifecycle_event_payloads", "AgentRuntimeLifecycleEventPayload"),
    "context_prepare_started": ("munk.services.operations.lifecycle_event_payloads", "AgentRuntimeLifecycleEventPayload"),
    "context_prepare_completed": ("munk.services.operations.lifecycle_event_payloads", "AgentRuntimeLifecycleEventPayload"),
    "context_prepare_start_state_ready": (
        "munk.services.operations.lifecycle_event_payloads",
        "AgentRuntimeLifecycleEventPayload",
    ),
    "context_prepare_params_resolved": (
        "munk.services.operations.lifecycle_event_payloads",
        "ContextPrepareParamsResolvedEventPayload",
    ),
    "context_prepare_device_ready": (
        "munk.services.operations.lifecycle_event_payloads",
        "ContextPrepareDeviceReadyEventPayload",
    ),
    "context_prepare_perception_ready": (
        "munk.services.operations.lifecycle_event_payloads",
        "ContextPreparePerceptionReadyEventPayload",
    ),
    "operation_submitted": ("munk.services.operations.lifecycle_event_payloads", "OperationSubmittedEventPayload"),
    "operation_started": ("munk.services.operations.lifecycle_event_payloads", "OperationStartedEventPayload"),
    "operation_interrupted": ("munk.services.operations.lifecycle_event_payloads", "OperationInterruptedEventPayload"),
    "resource_claimed": ("munk.services.operations.lifecycle_event_payloads", "ResourceClaimedEventPayload"),
    "resource_released": ("munk.services.operations.lifecycle_event_payloads", "ResourceReleasedEventPayload"),
    "resource_conflict": ("munk.services.operations.lifecycle_event_payloads", "ResourceConflictEventPayload"),
    "runner_context_loaded": ("munk.services.operations.lifecycle_event_payloads", "RunnerRuntimeEventPayload"),
    "judge_started": ("munk.services.operations.lifecycle_event_payloads", "JudgeRuntimeEventPayload"),
    "judge_context_loaded": ("munk.services.operations.lifecycle_event_payloads", "JudgeRuntimeEventPayload"),
    "judge_evidence_ready": ("munk.services.operations.lifecycle_event_payloads", "JudgeRuntimeEventPayload"),
    "judge_hard_rule_completed": ("munk.services.operations.lifecycle_event_payloads", "JudgeRuntimeEventPayload"),
    "judge_prompt_ready": ("munk.services.operations.lifecycle_event_payloads", "JudgeRuntimeEventPayload"),
    "judge_tool_calls_completed": ("munk.services.operations.lifecycle_event_payloads", "JudgeRuntimeEventPayload"),
    "judge_decision_ready": ("munk.services.operations.lifecycle_event_payloads", "JudgeRuntimeEventPayload"),
    "judge_completed": ("munk.services.operations.lifecycle_event_payloads", "JudgeRuntimeEventPayload"),
    "judge_canceled": ("munk.services.operations.lifecycle_event_payloads", "JudgeRuntimeEventPayload"),
    "judge_failed": ("munk.services.operations.lifecycle_event_payloads", "JudgeRuntimeEventPayload"),
    "llm_request": ("munk.services.operations.llm_timeline", "LlmRequestTimelinePayload"),
    "llm_response": ("munk.services.operations.llm_timeline", "LlmResponseTimelinePayload"),
    "workflow_started": ("munk.services.orchestration.event_payloads", "WorkflowStartedEventPayload"),
    "workflow_attempt_started": ("munk.services.orchestration.event_payloads", "WorkflowAttemptStartedEventPayload"),
    "judge_decision": ("munk.services.orchestration.event_payloads", "JudgeDecisionEventPayload"),
    "workflow_attempt_finished": ("munk.services.orchestration.event_payloads", "WorkflowAttemptFinishedEventPayload"),
    "workflow_retry_scheduled": ("munk.services.orchestration.event_payloads", "WorkflowRetryScheduledEventPayload"),
    "workflow_finished": ("munk.services.orchestration.event_payloads", "WorkflowFinishedEventPayload"),
    "plan_context_loaded": ("munk.services.planning.event_payloads", "PlanningTimelineEventPayload"),
    "plan_agent_ready": ("munk.services.planning.event_payloads", "PlanningTimelineEventPayload"),
    "plan_skeleton_generation_started": ("munk.services.planning.event_payloads", "PlanningTimelineEventPayload"),
    "plan_skeleton_generated": ("munk.services.planning.event_payloads", "PlanningTimelineEventPayload"),
    "plan_case_generation_started": ("munk.services.planning.event_payloads", "PlanningTimelineEventPayload"),
    "plan_case_generated": ("munk.services.planning.event_payloads", "PlanningTimelineEventPayload"),
    "plan_finalize_started": ("munk.services.planning.event_payloads", "PlanningTimelineEventPayload"),
    "plan_finalize_completed": ("munk.services.planning.event_payloads", "PlanningTimelineEventPayload"),
    "plan_skeleton_outline_warning": ("munk.services.planning.event_payloads", "PlanningTimelineEventPayload"),
    "plan_skeleton_ac_coverage_warning": ("munk.services.planning.event_payloads", "PlanningTimelineEventPayload"),
    "plan_saved": ("munk.services.planning.event_payloads", "PlanningTimelineEventPayload"),
    "change_plan_context_loaded": ("munk.services.planning.event_payloads", "PlanningTimelineEventPayload"),
    "change_plan_saved": ("munk.services.verify_change_event_payloads", "ChangeVerificationPlanSavedPayload"),
    "change_verification_review_contract_loaded": (
        "munk.services.verify_change_event_payloads",
        "ChangeVerificationReviewContractLoadedPayload",
    ),
    "change_verification_plan_saved": (
        "munk.services.verify_change_event_payloads",
        "ChangeVerificationPlanSavedPayload",
    ),
    "change_verification_cases_ready": (
        "munk.services.verify_change_event_payloads",
        "ChangeVerificationCasesReadyPayload",
    ),
    "review_context_loaded": ("munk.services.reviewing.event_payloads", "ReviewTimelineEventPayload"),
    "review_started": ("munk.services.reviewing.event_payloads", "ReviewTimelineEventPayload"),
    "review_request_built": ("munk.services.reviewing.event_payloads", "ReviewTimelineEventPayload"),
    "review_retrieval_completed": ("munk.services.reviewing.event_payloads", "ReviewTimelineEventPayload"),
    "review_agent_completed": ("munk.services.reviewing.event_payloads", "ReviewTimelineEventPayload"),
    "review_runtime_completed": ("munk.services.reviewing.event_payloads", "ReviewTimelineEventPayload"),
    "review_result_ready": ("munk.services.reviewing.event_payloads", "ReviewTimelineEventPayload"),
    "review_completed": ("munk.services.reviewing.event_payloads", "ReviewTimelineEventPayload"),
    "knowledge_started": ("munk.services.knowledge.event_payloads", "KnowledgeTimelineEventPayload"),
    "knowledge_evidence_ready": ("munk.services.knowledge.event_payloads", "KnowledgeTimelineEventPayload"),
    "knowledge_prompt_ready": ("munk.services.knowledge.event_payloads", "KnowledgeTimelineEventPayload"),
    "knowledge_agent_input_ready": ("munk.services.knowledge.event_payloads", "KnowledgeTimelineEventPayload"),
    "knowledge_tool_called": ("munk.services.knowledge.event_payloads", "KnowledgeTimelineEventPayload"),
    "knowledge_tool_calls_completed": ("munk.services.knowledge.event_payloads", "KnowledgeTimelineEventPayload"),
    "knowledge_result_generated": ("munk.services.knowledge.event_payloads", "KnowledgeTimelineEventPayload"),
    "knowledge_candidate_generation_completed": (
        "munk.services.knowledge.event_payloads",
        "KnowledgeTimelineEventPayload",
    ),
    "knowledge_runtime_completed": ("munk.services.knowledge.event_payloads", "KnowledgeTimelineEventPayload"),
    "knowledge_candidate_submission_completed": (
        "munk.services.knowledge.event_payloads",
        "KnowledgeTimelineEventPayload",
    ),
    "knowledge_result_ready": ("munk.services.knowledge.event_payloads", "KnowledgeTimelineEventPayload"),
    "knowledge_completed": ("munk.services.knowledge.event_payloads", "KnowledgeTimelineEventPayload"),
    "knowledge_skipped": ("munk.services.knowledge.event_payloads", "KnowledgeTimelineEventPayload"),
    "optimize_started": ("munk.services.optimization.event_payloads", "OptimizeTimelineEventPayload"),
    "optimize_request_built": ("munk.services.optimization.event_payloads", "OptimizeTimelineEventPayload"),
    "optimize_evidence_ready": ("munk.services.optimization.event_payloads", "OptimizeTimelineEventPayload"),
    "optimize_tool_called": ("munk.services.optimization.event_payloads", "OptimizeTimelineEventPayload"),
    "optimize_tool_calls_completed": ("munk.services.optimization.event_payloads", "OptimizeTimelineEventPayload"),
    "optimize_result_generated": ("munk.services.optimization.event_payloads", "OptimizeTimelineEventPayload"),
    "optimize_result_ready": ("munk.services.optimization.event_payloads", "OptimizeTimelineEventPayload"),
    "optimize_runtime_completed": ("munk.services.optimization.event_payloads", "OptimizeTimelineEventPayload"),
    "optimize_applied": ("munk.services.optimization.event_payloads", "OptimizeTimelineEventPayload"),
    "optimize_completed": ("munk.services.optimization.event_payloads", "OptimizeTimelineEventPayload"),
    "optimize_skipped": ("munk.services.optimization.event_payloads", "OptimizeTimelineEventPayload"),
    "optimize_failed": ("munk.services.optimization.event_payloads", "OptimizeTimelineEventPayload"),
    "batch_started": ("munk.services.running.timeline_event_payloads", "BatchStartedEventPayload"),
    "batch_child_started": ("munk.services.running.timeline_event_payloads", "BatchChildStartedEventPayload"),
    "batch_child_finished": ("munk.services.running.timeline_event_payloads", "BatchChildFinishedEventPayload"),
    "batch_stopped_early": ("munk.services.running.timeline_event_payloads", "BatchStoppedEarlyEventPayload"),
    "batch_finished": ("munk.services.running.timeline_event_payloads", "BatchFinishedEventPayload"),
    "child_operation_submitted": ("munk.services.running.operation_payloads", "PostRunChildOperationEventPayload"),
    "child_operation_submission_failed": (
        "munk.services.running.operation_payloads",
        "PostRunChildOperationEventPayload",
    ),
    "recording_started": ("munk.services.recording.event_payloads", "RecordingStartedEventPayload"),
    "recording_tap_observed": ("munk.services.recording.event_payloads", "RecordingTapObservedEventPayload"),
    "recording_interaction_recorded": (
        "munk.services.recording.event_payloads",
        "RecordingInteractionRecordedEventPayload",
    ),
    "recording_analysis_queued": ("munk.services.recording.event_payloads", "RecordingIdEventPayload"),
    "recording_case_exported": ("munk.services.recording.event_payloads", "RecordingCaseExportedEventPayload"),
    "recording_replay_linked": ("munk.services.recording.event_payloads", "RecordingReplayLinkedEventPayload"),
    "recording_bridge_cleanup_failed": (
        "munk.services.recording.event_payloads",
        "RecordingBridgeCleanupFailedEventPayload",
    ),
    "recording_analysis_started": ("munk.services.recording.event_payloads", "RecordingIdEventPayload"),
    "recording_analysis_failed": ("munk.services.recording.event_payloads", "RecordingAnalysisStatusEventPayload"),
    "recording_analysis_completed": (
        "munk.services.recording.event_payloads",
        "RecordingAnalysisStatusEventPayload",
    ),
    "recording_analysis_bundle_loaded": (
        "munk.services.recording.event_payloads",
        "RecordingAnalysisBundleLoadedEventPayload",
    ),
    "recording_analysis_step_started": (
        "munk.services.recording.event_payloads",
        "RecordingAnalysisStepEventPayload",
    ),
    "recording_analysis_step_completed": (
        "munk.services.recording.event_payloads",
        "RecordingAnalysisStepEventPayload",
    ),
    "recording_analysis_finalize_started": (
        "munk.services.recording.event_payloads",
        "RecordingAnalysisStepEventPayload",
    ),
    "recording_replay_started": ("munk.services.recording.event_payloads", "RecordingReplayStartedEventPayload"),
    "recording_replay_completed": (
        "munk.services.recording.event_payloads",
        "RecordingReplayCompletedEventPayload",
    ),
}


def operation_event_model_for(event_type: str) -> type[BaseModel] | None:
    model_path = _EVENT_PAYLOAD_MODEL_PATHS.get(event_type)
    if model_path is None:
        return None
    module_name, attr_name = model_path
    module = import_module(module_name)
    return cast(type[BaseModel], getattr(module, attr_name))


def serialize_operation_event_payload(event_type: str, raw_payload: object | None) -> dict[str, Any]:
    payload: object = {} if raw_payload is None else raw_payload
    if not isinstance(payload, dict):
        raise _payload_validation_error(
            event_type=event_type,
            model_name="dict",
            issues=["event payload must be a dict"],
        )
    payload_dict = cast(dict[str, Any], dict(payload))
    model_type = operation_event_model_for(event_type)
    if model_type is None:
        if payload_dict:
            raise _payload_validation_error(
                event_type=event_type,
                model_name="<unregistered>",
                issues=["unregistered event type must not carry structured payload"],
            )
        return {}
    try:
        model = model_type.model_validate(payload_dict)
    except ValidationError as exc:
        raise _payload_validation_error(
            event_type=event_type,
            model_name=model_type.__name__,
            issues=_validation_issues(exc),
        ) from exc
    return cast(dict[str, Any], model.model_dump(mode="json", exclude_none=True))


def _payload_validation_error(
    *,
    event_type: str,
    model_name: str,
    issues: list[str],
) -> OperationEventPayloadValidationError:
    return OperationEventPayloadValidationError(
        event_type=event_type,
        model_name=model_name,
        issues=issues,
    )


def _validation_issues(exc: ValidationError) -> list[str]:
    return [f"{'.'.join(str(item) for item in error['loc'])}: {error['msg']}" for error in exc.errors()] or [str(exc)]
