from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from munk.agent_base.llm import prepare_llm_transcript_path
from munk.agent_runtime import AgentRuntimeEvent, CancelController
from munk.planning.models import ChangePlanInput, RequirementInput
from munk.planning.runtime import PlanManagedPaths, PlanResolvedAppContext, PlanRuntimeContext
from munk.services.errors import AppAssetNotFoundError
from munk.services.knowledge import build_knowledge_provider_from_document, load_app_knowledge_document
from munk.services.running.paths import create_unique_run_dir


class PlanTrackerLike(Protocol):
    @property
    def operation_id(self) -> str | None: ...

    def append_event(self, *, event_type: str, message: str | None, data: dict[str, object] | None = None) -> None: ...

    def update_progress(self, **progress: object) -> None: ...

    def should_cancel(self) -> bool: ...


class TrackerPlanProgressSink:
    def __init__(self, tracker: PlanTrackerLike) -> None:
        self._tracker = tracker

    def emit(self, event: AgentRuntimeEvent) -> None:
        data = dict(event.data)
        data["lifecycle_state"] = event.lifecycle_state
        data["agent_role"] = event.agent_role
        data["timestamp"] = event.timestamp
        self._tracker.append_event(event_type=event.event_type, message=event.message, data=data)
        self._tracker.update_progress(
            lifecycle_state=event.lifecycle_state,
            agent_role=event.agent_role,
            event_timestamp=event.timestamp,
            **self._plan_progress_payload(event.event_type, data),
        )

    @staticmethod
    def _plan_progress_payload(event_type: str, data: dict[str, object]) -> dict[str, object]:
        progress: dict[str, object] = {"plan_event_type": event_type}
        stage_map = {
            "plan_context_loaded": "context_loaded",
            "plan_agent_ready": "agent_ready",
            "plan_skeleton_generation_started": "skeleton_generation_started",
            "plan_skeleton_generated": "skeleton_generated",
            "plan_case_generation_started": "case_generation_started",
            "plan_case_generated": "case_generated",
            "plan_finalize_started": "finalize_started",
            "plan_finalize_completed": "finalize_completed",
        }
        if event_type in stage_map:
            progress["stage"] = stage_map[event_type]
        for key in (
            "app_id",
            "plan_id",
            "plan_name",
            "target_case_count",
            "completed_case_count",
            "case_index",
            "case_id",
            "case_title",
        ):
            if key in data and data[key] is not None:
                progress[key] = data[key]
        return progress


class TrackerCancelController(CancelController):
    def __init__(self, tracker: PlanTrackerLike) -> None:
        self._tracker = tracker

    def is_cancel_requested(self) -> bool:
        return self._tracker.should_cancel()


@dataclass(frozen=True)
class PlanHostManagedPaths:
    root_dir: Path
    plan_path: Path
    snapshot_path: Path


@dataclass(frozen=True)
class BuiltPlanRuntimeContext:
    runtime_context: PlanRuntimeContext
    host_paths: PlanHostManagedPaths


@dataclass(frozen=True)
class PlanningStorageBundle:
    app_registry: object
    core_case_registry: object
    plan_store: object


def build_plan_runtime_context(*, tracker: PlanTrackerLike, request: RequirementInput | ChangePlanInput, storage) -> BuiltPlanRuntimeContext:  # noqa: ANN001
    root_dir = _resolve_root_dir(request)
    root_dir.mkdir(parents=True, exist_ok=True)
    app_profile, app_introduction, provider = _load_app_context(request.app_id, storage=storage)
    return BuiltPlanRuntimeContext(
        runtime_context=PlanRuntimeContext(
            operation_id=tracker.operation_id,
            managed_paths=PlanManagedPaths(
                root_dir=root_dir,
                request_dump_path=root_dir / "plan_request.json",
                llm_transcript_path=prepare_llm_transcript_path(root_dir),
            ),
            app_context=PlanResolvedAppContext(
                app_id=app_profile.app_id,
                platform=app_profile.platform,
                identity_label=app_profile.identity_label(),
                introduction=app_introduction,
                knowledge_tools=provider,
            ),
            progress=TrackerPlanProgressSink(tracker),
        ),
        host_paths=PlanHostManagedPaths(
            root_dir=root_dir,
            plan_path=root_dir / "plan.json",
            snapshot_path=root_dir / "snapshot.json",
        ),
    )


def build_plan_cancel_controller(*, tracker: PlanTrackerLike) -> CancelController:
    return TrackerCancelController(tracker)


def _load_app_context(app_id: str, *, storage):  # noqa: ANN001
    try:
        app_profile = storage.app_registry.load(app_id)
        app_introduction = storage.app_registry.load_introduction(app_id, ref=app_profile.app_introduction_ref)
    except FileNotFoundError as exc:
        raise AppAssetNotFoundError(str(exc)) from exc
    document = load_app_knowledge_document(
        app_id,
        registry=storage.app_registry,
        ref=app_profile.app_knowledge_ref,
    )
    if document is None:
        from munk.app_knowledge import AppKnowledgeImportDocument

        document = AppKnowledgeImportDocument(app_id=app_id, cards=[])
    return app_profile, app_introduction, build_knowledge_provider_from_document(document)


def _resolve_root_dir(request: RequirementInput | ChangePlanInput) -> Path:
    artifact_path = getattr(request, "artifact_path", None)
    if artifact_path is not None:
        return artifact_path
    return create_unique_run_dir(prefix="plan_run")
