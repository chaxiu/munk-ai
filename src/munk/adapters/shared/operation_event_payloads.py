from __future__ import annotations

from typing import cast

from pydantic import BaseModel, ConfigDict, ValidationError

from munk.services.errors import OperationEventPayloadValidationError
from munk.services.events import (
    LogEventPayload,
    PerceptionCompletedEventPayload,
    RunFailedEventPayload,
    RunnerActionEventPayload,
    RunnerContractMissEventPayload,
    RunnerDecisionCompletedEventPayload,
    RunnerToolCalledEventPayload,
    RunStartedEventPayload,
    RunStoppedEventPayload,
    StepStartedEventPayload,
)
from munk.services.knowledge.event_payloads import KnowledgeTimelineEventPayload
from munk.services.operations.lifecycle_event_payloads import (
    AgentRuntimeLifecycleEventPayload,
    ContextPrepareDeviceReadyEventPayload,
    ContextPrepareParamsResolvedEventPayload,
    ContextPreparePerceptionReadyEventPayload,
    JudgeRuntimeEventPayload,
    OperationInterruptedEventPayload,
    OperationStartedEventPayload,
    OperationSubmittedEventPayload,
    ResourceClaimedEventPayload,
    ResourceConflictEventPayload,
    ResourceReleasedEventPayload,
    RunnerRuntimeEventPayload,
)
from munk.services.operations.llm_timeline import LlmRequestTimelinePayload, LlmResponseTimelinePayload
from munk.services.optimization.event_payloads import OptimizeTimelineEventPayload
from munk.services.operations.event_payload_registry import operation_event_model_for
from munk.services.orchestration.event_payloads import (
    JudgeDecisionEventPayload,
    WorkflowAttemptFinishedEventPayload,
    WorkflowAttemptStartedEventPayload,
    WorkflowFinishedEventPayload,
    WorkflowRetryScheduledEventPayload,
    WorkflowStartedEventPayload,
)
from munk.services.planning.event_payloads import PlanningTimelineEventPayload
from munk.services.recording.event_payloads import (
    RecordingAnalysisBundleLoadedEventPayload,
    RecordingAnalysisStatusEventPayload,
    RecordingAnalysisStepEventPayload,
    RecordingBridgeCleanupFailedEventPayload,
    RecordingCaseExportedEventPayload,
    RecordingIdEventPayload,
    RecordingInteractionRecordedEventPayload,
    RecordingReplayCompletedEventPayload,
    RecordingReplayLinkedEventPayload,
    RecordingReplayStartedEventPayload,
    RecordingStartedEventPayload,
    RecordingTapObservedEventPayload,
)
from munk.services.reviewing.event_payloads import ReviewTimelineEventPayload
from munk.services.running.operation_payloads import PostRunChildOperationEventPayload
from munk.services.running.timeline_event_payloads import (
    BatchChildFinishedEventPayload,
    BatchChildStartedEventPayload,
    BatchFinishedEventPayload,
    BatchStartedEventPayload,
    BatchStoppedEarlyEventPayload,
)
from munk.services.verify_change_event_payloads import (
    ChangeVerificationCasesReadyPayload,
    ChangeVerificationPlanSavedPayload,
    ChangeVerificationReviewContractLoadedPayload,
)


class GenericOperationEventPayload(BaseModel):
    model_config = ConfigDict(extra="allow")


OperationEventPayloadData = (
    RunStartedEventPayload
    | StepStartedEventPayload
    | PerceptionCompletedEventPayload
    | RunnerToolCalledEventPayload
    | RunnerContractMissEventPayload
    | RunnerDecisionCompletedEventPayload
    | RunnerActionEventPayload
    | RunStoppedEventPayload
    | RunFailedEventPayload
    | LogEventPayload
    | LlmRequestTimelinePayload
    | LlmResponseTimelinePayload
    | WorkflowStartedEventPayload
    | WorkflowAttemptStartedEventPayload
    | WorkflowAttemptFinishedEventPayload
    | WorkflowRetryScheduledEventPayload
    | WorkflowFinishedEventPayload
    | JudgeDecisionEventPayload
    | AgentRuntimeLifecycleEventPayload
    | ContextPrepareParamsResolvedEventPayload
    | ContextPrepareDeviceReadyEventPayload
    | ContextPreparePerceptionReadyEventPayload
    | RunnerRuntimeEventPayload
    | JudgeRuntimeEventPayload
    | PostRunChildOperationEventPayload
    | OperationSubmittedEventPayload
    | OperationStartedEventPayload
    | OperationInterruptedEventPayload
    | ResourceClaimedEventPayload
    | ResourceReleasedEventPayload
    | ResourceConflictEventPayload
    | BatchStartedEventPayload
    | BatchChildStartedEventPayload
    | BatchChildFinishedEventPayload
    | BatchStoppedEarlyEventPayload
    | BatchFinishedEventPayload
    | PlanningTimelineEventPayload
    | ChangeVerificationReviewContractLoadedPayload
    | ChangeVerificationCasesReadyPayload
    | ChangeVerificationPlanSavedPayload
    | ReviewTimelineEventPayload
    | KnowledgeTimelineEventPayload
    | OptimizeTimelineEventPayload
    | RecordingIdEventPayload
    | RecordingStartedEventPayload
    | RecordingTapObservedEventPayload
    | RecordingInteractionRecordedEventPayload
    | RecordingCaseExportedEventPayload
    | RecordingReplayLinkedEventPayload
    | RecordingReplayStartedEventPayload
    | RecordingReplayCompletedEventPayload
    | RecordingBridgeCleanupFailedEventPayload
    | RecordingAnalysisStatusEventPayload
    | RecordingAnalysisBundleLoadedEventPayload
    | RecordingAnalysisStepEventPayload
    | GenericOperationEventPayload
)


def parse_operation_event_payload(*, event_type: str, raw_payload: object) -> OperationEventPayloadData | None:
    if not isinstance(raw_payload, dict) or not raw_payload:
        return None
    model_type = operation_event_model_for(event_type)
    if model_type is None:
        return GenericOperationEventPayload.model_validate(raw_payload)
    try:
        return cast(OperationEventPayloadData, model_type.model_validate(raw_payload))
    except ValidationError as exc:
        raise OperationEventPayloadValidationError(
            event_type=event_type,
            model_name=model_type.__name__,
            issues=[f"{'.'.join(str(item) for item in error['loc'])}: {error['msg']}" for error in exc.errors()] or [str(exc)],
        ) from exc
