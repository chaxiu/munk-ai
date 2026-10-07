from __future__ import annotations

import logging
from pathlib import Path
from threading import Thread
from typing import Any, Callable, cast

from munk.app import AppTarget
from munk.config.load import ResolvedConfig
from munk.recording import (
    ObservationSnapshot,
    ObservedTapCommand,
    RecordedInputEvent,
    RecordingAnalysisResult,
    RecordingCaseExport,
    RecordingReplayResult,
    RecordingSession,
    RecordingSessionStateError,
    RecordInteractionCommand,
    TimelineEntry,
)
from munk.recording_analysis import RecordingAnalysisService
from munk.services.operations.models import OperationRecord
from munk.services.operations.registry import OperationRegistry
from munk.services.operations.service import OperationService
from munk.services.recording.bridge_manager import RecordingBridgeManager, RecordingBridgeSession
from munk.services.recording.operation_payloads import (
    build_recording_analysis_operation_request_payload,
)
from munk.services.recording.runtime import resolve_recording_runtime
from munk.services.recording.session_support import AnalysisProgressCallback, RecordingSessionSupport

_logger = logging.getLogger(__name__)
_AnalysisProgressCallback = AnalysisProgressCallback


class RecordingSessionService:
    def __init__(
        self,
        *,
        project_root: Path,
        workspace_root: Path | None = None,
        registry: OperationRegistry | None = None,
        bridge_manager: RecordingBridgeManager | None = None,
        runtime_name: str | None = None,
        resolved_config: ResolvedConfig | None = None,
        analysis_runner: Callable[[dict[str, Any], _AnalysisProgressCallback | None], RecordingAnalysisResult] | None = None,
    ) -> None:
        self._project_root = project_root
        self._workspace_root = workspace_root or project_root
        self._registry = registry or OperationRegistry()
        self._operation_service = OperationService(self._registry)
        self._bridge_manager = bridge_manager or RecordingBridgeManager(project_root=project_root)
        self._runtime = resolve_recording_runtime(runtime_name=runtime_name)
        self._resolved_config = resolved_config
        self._analysis_service = RecordingAnalysisService(
            workspace_root=self._workspace_root,
            resolved_config=resolved_config,
        )
        self._analysis_runner = analysis_runner or self._analysis_service.analyze_bundle
        self._support = RecordingSessionSupport(
            runtime=self._runtime,
            registry=self._registry,
            operation_service=self._operation_service,
            bridge_manager=self._bridge_manager,
            workspace_root=self._workspace_root,
            resolved_config=self._resolved_config,
            logger=_logger,
            analyze_session=self._analyze_session_with_progress,
        )
        bind_analysis_runner = getattr(self._runtime, "bind_analysis_runner", None)
        if callable(bind_analysis_runner):
            bind_analysis_runner(self._analysis_runner)
        bind_replay_runner = getattr(self._runtime, "bind_replay_runner", None)
        if callable(bind_replay_runner):
            bind_replay_runner(self._support.replay_recording_case)

    @property
    def bridge_manager(self) -> RecordingBridgeManager:
        return self._bridge_manager

    def create_session(
        self,
        *,
        app_target: AppTarget,
        device_ref: str | None = None,
        case_id: str | None = None,
    ) -> RecordingSession:
        return self._runtime.create_session(
            app_target=app_target,
            device_ref=device_ref,
            case_id=case_id,
        )

    def begin_session(self, recording_id: str) -> tuple[RecordingSession, RecordingBridgeSession]:
        session = self._runtime.get_session(recording_id)
        if session.status != "created":
            raise RecordingSessionStateError(
                f"recording session '{recording_id}' cannot begin from status '{session.status}'"
            )
        tracker = self._support.create_operation_tracker(session)
        tracker.append_event(event_type="recording_begin_requested", message="recording begin requested")
        tracker.mark_running(pid=0, progress=self._support.progress_payload(session))
        try:
            started = self._runtime.begin_session(recording_id)
            bridge_session = self._bridge_manager.create_bridge_session(
                recording_id=recording_id,
                device_ref=started.device_ref,
            )
        except Exception as exc:
            try:
                latest = self._runtime.get_session(recording_id)
                if latest.status == "recording":
                    latest = self._runtime.cancel_session(recording_id)
                session = latest
            except Exception:
                pass
            tracker.mark_failed(
                error_code="recording_begin_failed",
                error_message=str(exc),
                artifacts=self._artifacts_payload(session),
                progress=self._support.progress_payload(session),
            )
            raise
        tracker.update_artifacts(self._artifacts_payload(started))
        tracker.update_progress(**self._support.progress_payload(started), bridge_status="running")
        tracker.append_event(
            event_type="recording_started",
            message="recording session started",
            data={"recording_id": recording_id, "bridge_ws_url": bridge_session.ws_url},
        )
        return started, bridge_session

    def get_session(self, recording_id: str) -> RecordingSession:
        return self._runtime.get_session(recording_id)

    def observe_tap(self, recording_id: str, command: ObservedTapCommand) -> RecordedInputEvent:
        event = self._runtime.record_tap(recording_id, command)
        session = self._runtime.get_session(recording_id)
        tracker = self._support.tracker_for(recording_id)
        if tracker is not None:
            tracker.append_event(
                event_type="recording_tap_observed",
                message=event.summary,
                data={
                    "event_id": event.event_id,
                    "kind": event.kind,
                    "payload": dict(event.payload),
                },
            )
            tracker.update_artifacts(self._artifacts_payload(session))
            progress = self._support.progress_payload(session)
            recorded_events = cast(list[RecordedInputEvent], self._runtime.list_recorded_events(recording_id))
            progress["latest_event_count"] = len(recorded_events)
            tracker.update_progress(**progress)
        return event

    def record_interaction(self, recording_id: str, command: RecordInteractionCommand) -> TimelineEntry:
        entry = self._runtime.record_interaction(recording_id, command)
        session = self._runtime.get_session(recording_id)
        tracker = self._support.tracker_for(recording_id)
        if tracker is not None:
            tracker.append_event(
                event_type="recording_interaction_recorded",
                message=entry.summary or entry.kind,
                data={
                    "entry_id": entry.entry_id,
                    "kind": entry.kind,
                    "forwarding_event_id": entry.forwarding_event_id,
                    "recording_event_id": entry.recording_event_id,
                    "before_observation_id": entry.before_observation_id,
                    "after_observation_id": entry.after_observation_id,
                    "after_stabilized": entry.after_stabilized,
                },
            )
            tracker.update_artifacts(self._artifacts_payload(session))
            progress = self._support.progress_payload(session)
            timeline_entries = cast(list[TimelineEntry], self._runtime.list_timeline(recording_id))
            progress["latest_timeline_count"] = len(timeline_entries)
            tracker.update_progress(**progress)
        return entry

    def list_recorded_events(
        self,
        recording_id: str,
        *,
        after_seq: int = 0,
        limit: int = 100,
    ) -> list[RecordedInputEvent]:
        return self._runtime.list_recorded_events(recording_id, after_seq=after_seq, limit=limit)

    def list_timeline(
        self,
        recording_id: str,
        *,
        after_seq: int = 0,
        limit: int = 100,
    ) -> list[TimelineEntry]:
        return self._runtime.list_timeline(recording_id, after_seq=after_seq, limit=limit)

    def get_observation(self, recording_id: str, observation_id: str) -> ObservationSnapshot:
        return self._runtime.get_observation(recording_id, observation_id)

    def submit_analysis(self, recording_id: str) -> OperationRecord:
        session = self._support.load_session_for_recording(recording_id)
        existing_operation = self.get_active_analysis_operation(recording_id)
        if existing_operation is not None:
            return existing_operation
        tracker = self._operation_service.create_operation(
            kind="recording_analysis",
            request_json=build_recording_analysis_operation_request_payload(
                recording_id=recording_id,
                app_id=session.app_id,
                case_id=session.case_id,
            ),
            app_id=session.app_id,
            case_id=session.case_id,
            requires_device=False,
        )
        tracker.update_progress(
            **self._support.analysis_progress_payload(
                recording_id=recording_id,
                phase="queued",
                analysis_status="queued",
            )
        )
        tracker.append_event(
            event_type="recording_analysis_queued",
            message="recording analysis queued",
            data={"recording_id": recording_id},
        )
        worker = Thread(
            target=self._run_analysis_operation,
            args=(tracker.operation_id, recording_id),
            name=f"recording-analysis-{recording_id}",
            daemon=True,
        )
        worker.start()
        return tracker.get_record()

    def analyze_session(
        self,
        recording_id: str,
        *,
        progress_callback: _AnalysisProgressCallback | None = None,
    ) -> RecordingAnalysisResult:
        analyze_recording = getattr(self._runtime, "analyze_recording")
        analysis = analyze_recording(recording_id, progress_callback=progress_callback)
        session = self._support.load_session_for_recording(recording_id)
        tracker = self._support.tracker_for(recording_id)
        if tracker is not None:
            event_type = "recording_analysis_completed" if analysis.status == "completed" else "recording_analysis_failed"
            message = "recording analysis completed" if analysis.status == "completed" else (
                analysis.failure_reason or "recording analysis failed"
            )
            tracker.append_event(event_type=event_type, message=message, data={"recording_id": recording_id, "analysis_status": analysis.status})
            tracker.update_artifacts(self._artifacts_payload(session))
            tracker.update_progress(**self._support.progress_payload(session), analysis_status=analysis.status)
        return analysis

    def get_analysis(self, recording_id: str) -> RecordingAnalysisResult | None:
        return self._support.load_analysis_for_recording(recording_id)

    def get_active_analysis_operation(self, recording_id: str) -> OperationRecord | None:
        operations = self._registry.list_operations(
            kind="recording_analysis",
            limit=20,
            query=recording_id,
        )
        for operation in operations:
            if operation.status not in {"queued", "running"}:
                continue
            request_json = cast(dict[str, Any], operation.request_json) if isinstance(operation.request_json, dict) else {}
            if request_json.get("recording_id") == recording_id:
                return operation
        return None

    def export_case(self, recording_id: str) -> RecordingCaseExport:
        session = self._support.load_session_for_recording(recording_id)
        export_result = self._runtime.export_case(recording_id)
        analysis = self._support.load_analysis_for_recording(recording_id)
        if analysis is None:
            analysis = self.analyze_session(recording_id)
        export_result = self._support.materialize_exported_plan(
            session=session,
            analysis=analysis,
            export_result=export_result,
        )
        tracker = self._support.tracker_for(recording_id)
        if tracker is not None:
            tracker.append_event(
                event_type="recording_case_exported",
                message="recording case exported",
                data={
                    "recording_id": recording_id,
                    "case_id": export_result.case_id,
                    "case_path": str(export_result.case_path),
                    "plan_id": export_result.plan_id,
                    "plan_path": str(export_result.plan_path) if export_result.plan_path is not None else None,
                },
            )
            tracker.update_artifacts(self._artifacts_payload(session))
            tracker.update_progress(
                **self._support.progress_payload(session),
                exported_case_id=export_result.case_id,
                exported_plan_id=export_result.plan_id,
            )
        return export_result

    def export_case_with_analysis(self, recording_id: str) -> tuple[RecordingAnalysisResult, RecordingCaseExport]:
        export_result = self.export_case(recording_id)
        analysis = self._support.load_analysis_for_recording(recording_id)
        if analysis is None:
            analysis = self.analyze_session(recording_id)
        return analysis, export_result

    def replay_case(self, recording_id: str) -> RecordingReplayResult:
        replay_result = self._runtime.replay_case(recording_id)
        session = self._support.load_session_for_recording(recording_id)
        tracker = self._support.tracker_for(recording_id)
        if tracker is not None:
            tracker.append_event(
                event_type="recording_replay_linked",
                message="recording replay linked",
                data={
                    "recording_id": recording_id,
                    "operation_id": replay_result.operation_id,
                    "verdict": replay_result.verdict,
                },
            )
            tracker.update_artifacts(self._artifacts_payload(session))
            tracker.update_progress(
                **self._support.progress_payload(session),
                replay_operation_id=replay_result.operation_id,
            )
        return replay_result

    def stop_session(self, recording_id: str) -> RecordingSession:
        return self._support.finalize_session_with_bridge_cleanup(
            recording_id=recording_id,
            finalizer=self._runtime.stop_session,
            success_event_type="recording_stopped",
            success_message="recording session stopped",
            warning_event_type="recording_stopped_with_bridge_warning",
            tracker_terminal_state="succeeded",
        )

    def cancel_session(self, recording_id: str) -> RecordingSession:
        return self._support.finalize_session_with_bridge_cleanup(
            recording_id=recording_id,
            finalizer=self._runtime.cancel_session,
            success_event_type="recording_cancelled",
            success_message="recording session cancelled",
            warning_event_type="recording_cancelled_with_bridge_warning",
            tracker_terminal_state="cancelled",
        )

    def shutdown(self) -> None:
        self._bridge_manager.shutdown()

    def _artifacts_payload(self, session: RecordingSession) -> dict[str, str]:
        return self._support.artifacts_payload(session)

    def _run_analysis_operation(self, operation_id: str, recording_id: str) -> None:
        self._support.run_analysis_operation(operation_id, recording_id)

    def _analyze_session_with_progress(
        self,
        recording_id: str,
        progress_callback: _AnalysisProgressCallback | None = None,
    ) -> RecordingAnalysisResult:
        return self.analyze_session(recording_id, progress_callback=progress_callback)
