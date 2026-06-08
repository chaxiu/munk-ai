from __future__ import annotations

import logging
import os
from pathlib import Path
from threading import Thread
from typing import Any, Callable, cast

from munk.app import AppTarget
from munk.config.load import ResolvedConfig
from munk.config.runtime import require_config_context
from munk.paths import assets_root
from munk.planning.models import RequirementPlan
from munk.planning.service import PLAN_VERSION
from munk.planning.storage import PlanStore
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
from munk.services.errors import OperationNotFoundError
from munk.services.operations.models import DeviceClaimRequest, OperationRecord, now_iso
from munk.services.operations.registry import OperationRegistry
from munk.services.operations.service import OperationService, OperationTracker
from munk.services.recording.bridge_manager import RecordingBridgeManager, RecordingBridgeSession
from munk.services.recording.replay_service import RecordingReplayService
from munk.services.recording.runtime import resolve_recording_runtime
from munk.testing import TestCase

_logger = logging.getLogger(__name__)
_AnalysisProgressCallback = Callable[[str, dict[str, Any]], None]


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
        self._replay_service: RecordingReplayService | None = None
        bind_analysis_runner = getattr(self._runtime, "bind_analysis_runner", None)
        if callable(bind_analysis_runner):
            bind_analysis_runner(self._analysis_runner)
        bind_replay_runner = getattr(self._runtime, "bind_replay_runner", None)
        if callable(bind_replay_runner):
            bind_replay_runner(self._replay_recording_case)

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
        tracker = self._create_operation_tracker(session)
        tracker.append_event(event_type="recording_begin_requested", message="recording begin requested")
        tracker.mark_running(pid=0, progress=self._progress_payload(session))
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
                progress=self._progress_payload(session),
            )
            raise
        tracker.update_artifacts(self._artifacts_payload(started))
        tracker.update_progress(**self._progress_payload(started), bridge_status="running")
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
        tracker = self._tracker_for(recording_id)
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
            progress = self._progress_payload(session)
            recorded_events = cast(list[RecordedInputEvent], self._runtime.list_recorded_events(recording_id))
            progress["latest_event_count"] = len(recorded_events)
            tracker.update_progress(**progress)
        return event

    def record_interaction(self, recording_id: str, command: RecordInteractionCommand) -> TimelineEntry:
        entry = self._runtime.record_interaction(recording_id, command)
        session = self._runtime.get_session(recording_id)
        tracker = self._tracker_for(recording_id)
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
            progress = self._progress_payload(session)
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
        session = self._load_session_for_recording(recording_id)
        existing_operation = self.get_active_analysis_operation(recording_id)
        if existing_operation is not None:
            return existing_operation
        tracker = self._operation_service.create_operation(
            kind="recording_analysis",
            request_json={
                "recording_id": recording_id,
                "app_id": session.app_id,
                "case_id": session.case_id,
            },
            app_id=session.app_id,
            case_id=session.case_id,
            requires_device=False,
        )
        tracker.update_progress(
            **self._analysis_progress_payload(
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
        session = self._load_session_for_recording(recording_id)
        tracker = self._tracker_for(recording_id)
        if tracker is not None:
            event_type = "recording_analysis_completed" if analysis.status == "completed" else "recording_analysis_failed"
            message = "recording analysis completed" if analysis.status == "completed" else (
                analysis.failure_reason or "recording analysis failed"
            )
            tracker.append_event(event_type=event_type, message=message, data={"recording_id": recording_id, "analysis_status": analysis.status})
            tracker.update_artifacts(self._artifacts_payload(session))
            tracker.update_progress(**self._progress_payload(session), analysis_status=analysis.status)
        return analysis

    def get_analysis(self, recording_id: str) -> RecordingAnalysisResult | None:
        return self._load_analysis_for_recording(recording_id)

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
        session = self._load_session_for_recording(recording_id)
        export_result = self._runtime.export_case(recording_id)
        analysis = self._load_analysis_for_recording(recording_id)
        if analysis is None:
            analysis = self.analyze_session(recording_id)
        export_result = self._materialize_exported_plan(
            session=session,
            analysis=analysis,
            export_result=export_result,
        )
        tracker = self._tracker_for(recording_id)
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
                **self._progress_payload(session),
                exported_case_id=export_result.case_id,
                exported_plan_id=export_result.plan_id,
            )
        return export_result

    def export_case_with_analysis(self, recording_id: str) -> tuple[RecordingAnalysisResult, RecordingCaseExport]:
        export_result = self.export_case(recording_id)
        analysis = self._load_analysis_for_recording(recording_id)
        if analysis is None:
            analysis = self.analyze_session(recording_id)
        return analysis, export_result

    def replay_case(self, recording_id: str) -> RecordingReplayResult:
        replay_result = self._runtime.replay_case(recording_id)
        session = self._load_session_for_recording(recording_id)
        tracker = self._tracker_for(recording_id)
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
            tracker.update_progress(**self._progress_payload(session), replay_operation_id=replay_result.operation_id)
        return replay_result

    def stop_session(self, recording_id: str) -> RecordingSession:
        return self._finalize_session_with_bridge_cleanup(
            recording_id=recording_id,
            finalizer=self._runtime.stop_session,
            success_event_type="recording_stopped",
            success_message="recording session stopped",
            warning_event_type="recording_stopped_with_bridge_warning",
            tracker_terminal_state="succeeded",
        )

    def cancel_session(self, recording_id: str) -> RecordingSession:
        return self._finalize_session_with_bridge_cleanup(
            recording_id=recording_id,
            finalizer=self._runtime.cancel_session,
            success_event_type="recording_cancelled",
            success_message="recording session cancelled",
            warning_event_type="recording_cancelled_with_bridge_warning",
            tracker_terminal_state="cancelled",
        )

    def shutdown(self) -> None:
        self._bridge_manager.shutdown()

    def _create_operation_tracker(self, session: RecordingSession) -> OperationTracker:
        request_json: dict[str, Any] = {
            "recording_id": session.recording_id,
            "app_id": session.app_id,
            "entry_identity": session.app_target.entry_identity,
            "device_ref": session.device_ref,
        }
        record = OperationRecord(
            operation_id=session.recording_id,
            kind="record_case",
            status="queued",
            app_id=session.app_id,
            case_id=session.case_id,
            request_json=request_json,
            device_ref=session.device_ref,
            resource_scope="device_ref" if session.device_ref else "device_unspecified",
        )
        claim_request = DeviceClaimRequest(
            device_ref=session.device_ref,
            resource_scope=record.resource_scope,
        )
        self._registry.create_operation_with_claim(record, claim_request=claim_request)
        return OperationTracker(self._registry, session.recording_id)

    def _tracker_for(self, recording_id: str) -> OperationTracker | None:
        try:
            self._registry.get_operation(recording_id)
        except OperationNotFoundError:
            return None
        return OperationTracker(self._registry, recording_id)

    def _artifacts_payload(self, session: RecordingSession) -> dict[str, str]:
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
        export_result = self._load_export_manifest_for_recording(session.recording_id)
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

    def _progress_payload(self, session: RecordingSession) -> dict[str, Any]:
        recorded_events: list[RecordedInputEvent] = list(self._runtime.list_recorded_events(session.recording_id))
        event_count = len(recorded_events)
        list_timeline = getattr(self._runtime, "list_timeline", None)
        timeline_entries: list[TimelineEntry] = []
        if callable(list_timeline):
            timeline_entries = list(cast(list[TimelineEntry], list_timeline(session.recording_id)))
        timeline_count = len(timeline_entries)
        return {
            "recording_id": session.recording_id,
            "status": session.status,
            "latest_frame_seq": session.latest_frame_seq,
            "latest_event_count": event_count,
            "latest_timeline_count": timeline_count,
            "updated_at": now_iso(),
        }

    def _finalize_session_with_bridge_cleanup(
        self,
        *,
        recording_id: str,
        finalizer: Callable[[str], RecordingSession],
        success_event_type: str,
        success_message: str,
        warning_event_type: str,
        tracker_terminal_state: str,
    ) -> RecordingSession:
        finalized: RecordingSession = finalizer(recording_id)
        tracker = self._tracker_for(recording_id)
        bridge_error: Exception | None = None
        try:
            self._bridge_manager.stop_bridge_session(recording_id=recording_id)
        except Exception as exc:  # pragma: no cover - defensive path is asserted via service tests
            bridge_error = exc
            _logger.warning(
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
        if tracker is not None:
            tracker.append_event(
                event_type=warning_event_type if bridge_error is not None else success_event_type,
                message=success_message if bridge_error is None else f"{success_message} (bridge cleanup warning)",
            )
            if tracker_terminal_state == "succeeded":
                tracker.mark_succeeded(
                    verification_verdict=None,
                    result_json={"recording_id": recording_id, "status": finalized.status},
                    artifacts=self._artifacts_payload(finalized),
                    progress=self._progress_payload(finalized),
                )
            else:
                tracker.mark_cancelled(
                    result_json={"recording_id": recording_id, "status": finalized.status},
                    artifacts=self._artifacts_payload(finalized),
                    progress=self._progress_payload(finalized),
                )
        return finalized

    def _load_session_for_recording(self, recording_id: str) -> RecordingSession:
        load_recording_assets = getattr(self._runtime, "load_recording_assets", None)
        if callable(load_recording_assets):
            raw_bundle = cast(object, load_recording_assets(recording_id))
            if isinstance(raw_bundle, dict):
                bundle_dict = cast(dict[str, object], raw_bundle)
                session_payload = bundle_dict.get("session")
                if isinstance(session_payload, dict):
                    session_payload_dict = cast(dict[str, object], session_payload)
                    return RecordingSession.model_validate(session_payload_dict)
        return self._runtime.get_session(recording_id)

    def _load_analysis_for_recording(self, recording_id: str) -> RecordingAnalysisResult | None:
        load_analysis_result = getattr(self._runtime, "load_analysis_result", None)
        if callable(load_analysis_result):
            return cast(RecordingAnalysisResult | None, load_analysis_result(recording_id))
        return None

    def _load_export_manifest_for_recording(self, recording_id: str) -> RecordingCaseExport | None:
        load_export_manifest = getattr(self._runtime, "load_export_manifest", None)
        if callable(load_export_manifest):
            return cast(RecordingCaseExport | None, load_export_manifest(recording_id))
        return None

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

    def _materialize_exported_plan(
        self,
        *,
        session: RecordingSession,
        analysis: RecordingAnalysisResult,
        export_result: RecordingCaseExport,
    ) -> RecordingCaseExport:
        test_case = analysis.test_case
        if test_case is None:
            raise RuntimeError("recording export requires a canonical test case")
        case_metadata = {
            **dict(test_case.source_metadata),
            **self._build_recording_source_metadata(session=session, export_result=export_result),
        }
        exported_case = test_case.model_copy(update={"source_metadata": case_metadata})
        plan = RequirementPlan(
            plan_id=f"recording_{session.recording_id}",
            name=test_case.title,
            app_id=session.app_id,
            source="recording_export",
            version=PLAN_VERSION,
            cases=[exported_case],
            source_metadata=self._build_recording_source_metadata(session=session, export_result=export_result),
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

    def _run_analysis_operation(self, operation_id: str, recording_id: str) -> None:
        tracker = self._operation_service.get_tracker(operation_id)
        tracker.mark_running(
            pid=os.getpid(),
            progress=self._analysis_progress_payload(
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
        session = self._load_session_for_recording(recording_id)
        try:
            analysis = self.analyze_session(
                recording_id,
                progress_callback=lambda stage, payload: self._handle_analysis_progress(
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
                artifacts=self._artifacts_payload(session),
                progress=self._analysis_progress_payload(
                    recording_id=recording_id,
                    phase="failed",
                    analysis_status="failed",
                ),
            )
            return
        session = self._load_session_for_recording(recording_id)
        progress = self._analysis_progress_payload(
            recording_id=recording_id,
            phase="completed" if analysis.status == "completed" else "failed",
            analysis_status=analysis.status,
            total_steps=len(analysis.steps or []),
            completed_steps=len(analysis.steps or []),
        )
        artifacts = self._artifacts_payload(session)
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

    def _handle_analysis_progress(
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
                **self._analysis_progress_payload(
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
                **self._analysis_progress_payload(
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
                **self._analysis_progress_payload(
                    recording_id=recording_id,
                    phase="analyzing_steps",
                    analysis_status="running",
                    total_steps=total_steps,
                    completed_steps=completed_steps,
                    current_step_seq=current_step_seq,
                )
            )
            return
        if stage == "finalize_started":
            tracker.append_event(
                event_type="recording_analysis_finalize_started",
                message="recording analysis finalization started",
                data={"recording_id": recording_id, **payload},
            )
            tracker.update_progress(
                **self._analysis_progress_payload(
                    recording_id=recording_id,
                    phase="finalizing",
                    analysis_status="running",
                    total_steps=total_steps,
                    completed_steps=completed_steps,
                    current_step_seq=current_step_seq,
                )
            )

    def _analysis_progress_payload(
        self,
        *,
        recording_id: str,
        phase: str,
        analysis_status: str,
        total_steps: int = 0,
        completed_steps: int = 0,
        current_step_seq: int | None = None,
    ) -> dict[str, Any]:
        return {
            "recording_id": recording_id,
            "phase": phase,
            "analysis_status": analysis_status,
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "current_step_seq": current_step_seq,
            "updated_at": now_iso(),
        }

    def _load_export_case_path(self, recording_id: str, session: RecordingSession) -> Path:
        load_export_manifest = getattr(self._runtime, "load_export_manifest", None)
        if callable(load_export_manifest):
            export_manifest = cast(RecordingCaseExport | None, load_export_manifest(recording_id))
            if export_manifest is not None:
                return export_manifest.case_path
        return session.asset_dir / "case" / "test_case.json"

    def _resolve_replay_service(self) -> RecordingReplayService:
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

    def _replay_recording_case(
        self,
        recording_id: str,
        session: RecordingSession,
        test_case: TestCase,
    ) -> RecordingReplayResult:
        return self._resolve_replay_service().replay_case(
            recording_id=recording_id,
            session=session,
            test_case=test_case,
            test_case_path=self._load_export_case_path(recording_id, session),
        )
