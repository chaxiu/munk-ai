from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Callable, cast

from munk.config.load import ResolvedConfig
from munk.config.runtime import require_config_context
from munk.paths import assets_root
from munk.planning.models import RequirementPlan
from munk.planning.service import PLAN_VERSION
from munk.planning.storage import PlanStore
from munk.recording import (
    RecordedInputEvent,
    RecordingAnalysisResult,
    RecordingCaseExport,
    RecordingReplayResult,
    RecordingRuntime,
    RecordingSession,
    TimelineEntry,
)
from munk.services.case_validation import validate_case_definition
from munk.services.errors import OperationNotFoundError
from munk.services.operations.models import now_iso
from munk.services.operations.registry import OperationRegistry
from munk.services.operations.service import OperationService, OperationTracker
from munk.services.recording.bridge_manager import RecordingBridgeManager
from munk.services.recording.operation_payloads import (
    build_recording_analysis_progress_payload,
    build_recording_session_operation_request_payload,
    build_recording_session_progress_payload,
    build_recording_session_terminal_result_payload,
)
from munk.services.recording.replay_service import RecordingReplayService
from munk.testing import TestCase

AnalysisProgressCallback = Callable[[str, dict[str, Any]], None]


class RecordingSessionSupport:
    def __init__(
        self,
        *,
        runtime: RecordingRuntime,
        registry: OperationRegistry,
        operation_service: OperationService,
        bridge_manager: RecordingBridgeManager,
        workspace_root: Path,
        resolved_config: ResolvedConfig | None,
        logger: logging.Logger,
        analyze_session: Callable[[str, AnalysisProgressCallback | None], RecordingAnalysisResult],
    ) -> None:
        self._runtime = runtime
        self._registry = registry
        self._operation_service = operation_service
        self._bridge_manager = bridge_manager
        self._workspace_root = workspace_root
        self._resolved_config = resolved_config
        self._logger = logger
        self._analyze_session = analyze_session
        self._replay_service: RecordingReplayService | None = None

    def create_operation_tracker(self, session: RecordingSession) -> OperationTracker:
        return self._operation_service.create_operation(
            operation_id=session.recording_id,
            kind="record_case",
            request_json=build_recording_session_operation_request_payload(session),
            app_id=session.app_id,
            plan_id=None,
            case_id=session.case_id,
            requires_device=True,
            device_ref=session.device_ref,
        )

    def tracker_for(self, recording_id: str) -> OperationTracker | None:
        try:
            self._registry.get_operation(recording_id)
        except OperationNotFoundError:
            return None
        return OperationTracker(self._registry, recording_id)

    def artifacts_payload(self, session: RecordingSession) -> dict[str, str]:
        artifacts: dict[str, str] = {
            "recording_dir": str(session.asset_dir),
            "session_json": str(session.asset_dir / "session.json"),
            "manifest_json": str(session.asset_dir / "manifest.json"),
        }
        analysis_path = session.asset_dir / "case" / "analysis.json"
        test_case_path = session.asset_dir / "case" / "test_case.json"
        export_manifest_path = session.asset_dir / "case" / "export_manifest.json"
        replay_manifest_path = session.asset_dir / "case" / "replay_manifest.json"
        if analysis_path.exists():
            artifacts["analysis_json"] = str(analysis_path)
        if test_case_path.exists():
            artifacts["test_case_json"] = str(test_case_path)
        if export_manifest_path.exists():
            artifacts["recording_case_manifest"] = str(export_manifest_path)
        if replay_manifest_path.exists():
            artifacts["recording_replay_manifest"] = str(replay_manifest_path)
        export_result = self.load_export_manifest_for_recording(session.recording_id)
        if export_result is not None and export_result.plan_path is not None:
            artifacts["plan_json"] = str(export_result.plan_path)
        if export_result is not None and export_result.snapshot_path is not None:
            artifacts["plan_snapshot"] = str(export_result.snapshot_path)
        plan_path = assets_root() / "plans" / session.app_id / f"recording_{session.recording_id}.json"
        if "plan_json" not in artifacts and plan_path.exists():
            artifacts["plan_json"] = str(plan_path)
        snapshot_dir = plan_path.parent / "snapshots"
        if "plan_snapshot" not in artifacts and snapshot_dir.exists():
            snapshots = sorted(snapshot_dir.glob(f"recording_{session.recording_id}-*.json"))
            if snapshots:
                artifacts["plan_snapshot"] = str(snapshots[-1])
        return artifacts

    def progress_payload(self, session: RecordingSession) -> dict[str, Any]:
        recorded_events = list(self._runtime.list_recorded_events(session.recording_id))
        list_timeline = getattr(self._runtime, "list_timeline", None)
        timeline_entries: list[TimelineEntry] = []
        if callable(list_timeline):
            timeline_entries = list(cast(list[TimelineEntry], list_timeline(session.recording_id)))
        return build_recording_session_progress_payload(
            session=session,
            latest_event_count=len(recorded_events),
            latest_timeline_count=len(timeline_entries),
            updated_at=now_iso(),
        )

    def finalize_session_with_bridge_cleanup(
        self,
        *,
        recording_id: str,
        finalizer: Callable[[str], RecordingSession],
        success_event_type: str,
        success_message: str,
        warning_event_type: str,
        tracker_terminal_state: str,
    ) -> RecordingSession:
        finalized = finalizer(recording_id)
        tracker = self.tracker_for(recording_id)
        bridge_error: Exception | None = None
        try:
            self._bridge_manager.stop_bridge_session(recording_id=recording_id)
        except Exception as exc:  # pragma: no cover - defensive path is asserted via service tests
            bridge_error = exc
            self._logger.warning(
                "recording bridge cleanup failed for '%s' after session reached '%s': %s",
                recording_id,
                finalized.status,
                exc,
            )
            if tracker is not None:
                tracker.append_event(
                    event_type="recording_bridge_cleanup_failed",
                    message="recording bridge cleanup failed after finalization",
                    data={"recording_id": recording_id, "error": str(exc), "status": finalized.status},
                )
        if tracker is None:
            return finalized
        tracker.append_event(
            event_type=warning_event_type if bridge_error is not None else success_event_type,
            message=success_message if bridge_error is None else f"{success_message} (bridge cleanup warning)",
        )
        terminal_result = build_recording_session_terminal_result_payload(
            recording_id=recording_id,
            status=finalized.status,
        )
        artifacts = self.artifacts_payload(finalized)
        progress = self.progress_payload(finalized)
        if tracker_terminal_state == "succeeded":
            tracker.mark_succeeded(
                verification_verdict=None,
                result_json=terminal_result,
                artifacts=artifacts,
                progress=progress,
            )
            return finalized
        tracker.mark_cancelled(
            result_json=terminal_result,
            artifacts=artifacts,
            progress=progress,
        )
        return finalized

    def load_session_for_recording(self, recording_id: str) -> RecordingSession:
        load_recording_assets = getattr(self._runtime, "load_recording_assets", None)
        if callable(load_recording_assets):
            raw_bundle = cast(object, load_recording_assets(recording_id))
            if isinstance(raw_bundle, dict):
                session_payload = raw_bundle.get("session")
                if isinstance(session_payload, dict):
                    return RecordingSession.model_validate(session_payload)
        return self._runtime.get_session(recording_id)

    def load_analysis_for_recording(self, recording_id: str) -> RecordingAnalysisResult | None:
        load_analysis_result = getattr(self._runtime, "load_analysis_result", None)
        if callable(load_analysis_result):
            return cast(RecordingAnalysisResult | None, load_analysis_result(recording_id))
        return None

    def load_export_manifest_for_recording(self, recording_id: str) -> RecordingCaseExport | None:
        load_export_manifest = getattr(self._runtime, "load_export_manifest", None)
        if callable(load_export_manifest):
            return cast(RecordingCaseExport | None, load_export_manifest(recording_id))
        return None

    def materialize_exported_plan(
        self,
        *,
        session: RecordingSession,
        analysis: RecordingAnalysisResult,
        export_result: RecordingCaseExport,
    ) -> RecordingCaseExport:
        test_case = analysis.test_case
        if test_case is None:
            raise RuntimeError("recording export requires a canonical test case")
        validated_case = validate_case_definition(
            test_case,
            context=f"recording session export for '{session.recording_id}'",
        )
        recording_metadata = self._build_recording_source_metadata(
            session=session,
            export_result=export_result,
        )
        exported_case = validated_case.model_copy(
            update={
                "source_metadata": {
                    **dict(validated_case.source_metadata),
                    **recording_metadata,
                }
            }
        )
        plan = RequirementPlan(
            plan_id=f"recording_{session.recording_id}",
            name=validated_case.title,
            app_id=session.app_id,
            source="recording_export",
            version=PLAN_VERSION,
            cases=[exported_case],
            source_metadata=recording_metadata,
        )
        plan_store = PlanStore(root_dir=assets_root())
        plan_path = plan_store.save(plan)
        snapshot_path = plan_store.export_snapshot(plan)
        return export_result.model_copy(
            update={
                "plan_id": plan.plan_id,
                "plan_path": plan_path,
                "snapshot_path": snapshot_path,
            }
        )

    def run_analysis_operation(self, operation_id: str, recording_id: str) -> None:
        tracker = self._operation_service.get_tracker(operation_id)
        tracker.mark_running(
            pid=os.getpid(),
            progress=self.analysis_progress_payload(
                recording_id=recording_id,
                phase="loading",
                analysis_status="running",
            ),
        )
        tracker.append_event(
            event_type="recording_analysis_started",
            message="recording analysis started",
            data={"recording_id": recording_id},
        )
        session = self.load_session_for_recording(recording_id)
        try:
            analysis = self._analyze_session(
                recording_id,
                lambda stage, payload: self.handle_analysis_progress(
                    tracker,
                    recording_id=recording_id,
                    stage=stage,
                    payload=payload,
                ),
            )
        except Exception as exc:
            tracker.append_event(
                event_type="recording_analysis_failed",
                message=str(exc),
                data={"recording_id": recording_id},
            )
            tracker.mark_failed(
                error_code="recording_analysis_failed",
                error_message=str(exc),
                artifacts=self.artifacts_payload(session),
                progress=self.analysis_progress_payload(
                    recording_id=recording_id,
                    phase="failed",
                    analysis_status="failed",
                ),
            )
            return
        session = self.load_session_for_recording(recording_id)
        progress = self.analysis_progress_payload(
            recording_id=recording_id,
            phase="completed" if analysis.status == "completed" else "failed",
            analysis_status=analysis.status,
            total_steps=len(analysis.steps or []),
            completed_steps=len(analysis.steps or []),
        )
        artifacts = self.artifacts_payload(session)
        if analysis.status == "completed":
            tracker.append_event(
                event_type="recording_analysis_completed",
                message="recording analysis completed",
                data={"recording_id": recording_id, "analysis_status": analysis.status},
            )
            tracker.mark_succeeded(
                verification_verdict=None,
                result_json=analysis.model_dump(mode="json"),
                artifacts=artifacts,
                progress=progress,
            )
            return
        failure_reason = analysis.failure_reason or "recording analysis failed"
        tracker.append_event(
            event_type="recording_analysis_failed",
            message=failure_reason,
            data={"recording_id": recording_id, "analysis_status": analysis.status},
        )
        tracker.mark_failed(
            error_code="recording_analysis_failed",
            error_message=failure_reason,
            artifacts=artifacts,
            progress=progress,
        )

    def handle_analysis_progress(
        self,
        tracker: OperationTracker,
        *,
        recording_id: str,
        stage: str,
        payload: dict[str, Any],
    ) -> None:
        total_steps = cast(int, payload.get("total_steps") or 0)
        completed_steps = cast(int, payload.get("completed_steps") or 0)
        current_step_seq = cast(int | None, payload.get("current_step_seq"))
        if stage == "bundle_loaded":
            tracker.append_event(
                event_type="recording_analysis_bundle_loaded",
                message="recording analysis bundle loaded",
                data={"recording_id": recording_id, "total_steps": total_steps},
            )
            tracker.update_progress(
                **self.analysis_progress_payload(
                    recording_id=recording_id,
                    phase="loading",
                    analysis_status="running",
                    total_steps=total_steps,
                    completed_steps=completed_steps,
                    current_step_seq=current_step_seq,
                )
            )
            return
        if stage == "step_started":
            tracker.append_event(
                event_type="recording_analysis_step_started",
                message=f"recording analysis step {current_step_seq} started",
                data={"recording_id": recording_id, **payload},
            )
            tracker.update_progress(
                **self.analysis_progress_payload(
                    recording_id=recording_id,
                    phase="analyzing_steps",
                    analysis_status="running",
                    total_steps=total_steps,
                    completed_steps=completed_steps,
                    current_step_seq=current_step_seq,
                )
            )
            return
        if stage == "step_completed":
            tracker.append_event(
                event_type="recording_analysis_step_completed",
                message=f"recording analysis step {current_step_seq} completed",
                data={"recording_id": recording_id, **payload},
            )
            tracker.update_progress(
                **self.analysis_progress_payload(
                    recording_id=recording_id,
                    phase="analyzing_steps",
                    analysis_status="running",
                    total_steps=total_steps,
                    completed_steps=completed_steps,
                    current_step_seq=current_step_seq,
                )
            )
            return
        if stage != "finalize_started":
            return
        tracker.append_event(
            event_type="recording_analysis_finalize_started",
            message="recording analysis finalization started",
            data={"recording_id": recording_id, **payload},
        )
        tracker.update_progress(
            **self.analysis_progress_payload(
                recording_id=recording_id,
                phase="finalizing",
                analysis_status="running",
                total_steps=total_steps,
                completed_steps=completed_steps,
                current_step_seq=current_step_seq,
            )
        )

    def analysis_progress_payload(
        self,
        *,
        recording_id: str,
        phase: str,
        analysis_status: str,
        total_steps: int = 0,
        completed_steps: int = 0,
        current_step_seq: int | None = None,
    ) -> dict[str, Any]:
        return build_recording_analysis_progress_payload(
            recording_id=recording_id,
            phase=phase,
            analysis_status=analysis_status,
            total_steps=total_steps,
            completed_steps=completed_steps,
            current_step_seq=current_step_seq,
            updated_at=now_iso(),
        )

    def replay_recording_case(
        self,
        recording_id: str,
        session: RecordingSession,
        test_case: TestCase,
    ) -> RecordingReplayResult:
        return self.resolve_replay_service().replay_case(
            recording_id=recording_id,
            session=session,
            test_case=test_case,
            test_case_path=self.load_export_case_path(recording_id, session),
        )

    def load_export_case_path(self, recording_id: str, session: RecordingSession) -> Path:
        export_manifest = self.load_export_manifest_for_recording(recording_id)
        if export_manifest is not None:
            return export_manifest.case_path
        return session.asset_dir / "case" / "test_case.json"

    def resolve_replay_service(self) -> RecordingReplayService:
        if self._replay_service is not None:
            return self._replay_service
        resolved_config = self._resolved_config or require_config_context(
            cli_path=None,
            workspace_root=self._workspace_root,
            command_name="recording replay",
        )
        self._replay_service = RecordingReplayService(
            resolved_config=resolved_config,
            operation_service=self._operation_service,
        )
        return self._replay_service

    def _build_recording_source_metadata(
        self,
        *,
        session: RecordingSession,
        export_result: RecordingCaseExport,
    ) -> dict[str, str]:
        metadata = {
            "origin": "recording",
            "recording_id": session.recording_id,
            "recording_asset_dir": str(session.asset_dir),
            "recording_analysis_path": str(export_result.analysis_path),
            "recording_case_path": str(export_result.case_path),
            "recording_exported_at": export_result.exported_at,
        }
        if export_result.plan_path is not None:
            metadata["recording_plan_path"] = str(export_result.plan_path)
        if export_result.snapshot_path is not None:
            metadata["recording_snapshot_path"] = str(export_result.snapshot_path)
        return metadata
