from __future__ import annotations

from dataclasses import dataclass
from threading import Event, Lock, Thread
from typing import Any, Callable, cast

from munk.app import AppTarget
from munk.recording import (
    ForwardingEvent,
    LiveViewFrame,
    ObservationSnapshot,
    ObservedTapCommand,
    RecordedInputEvent,
    RecordingAnalysisResult,
    RecordingAssetManifest,
    RecordingCaseExport,
    RecordingReplayResult,
    RecordingRuntimeHealth,
    RecordingSession,
    RecordingSessionNotFoundError,
    RecordingSessionStateError,
    RecordInteractionCommand,
    TimelineEntry,
    validate_record_interaction_contract,
)
from munk.recording.models import now_iso
from munk.services.case_validation import validate_case_definition
from munk.services.errors import InvalidCaseDefinitionError
from munk.testing import TestCase

from .analysis import build_recording_asset_bundle
from .android_backend import AndroidRecordingBackend
from .exporter import export_analysis_case
from .interaction_builders import build_forwarding_event, build_recording_event, tap_to_interaction
from .observation_capture import ObservationCaptureCoordinator
from .paths import ensure_recording_assets_home
from .store import RecordingStore

DEFAULT_CAPTURE_INTERVAL_SECONDS = 1.0
DEFAULT_STABILIZATION_INTERVAL_SECONDS = 0.2
DEFAULT_STABILIZATION_TIMEOUT_SECONDS = 2.0
BackendFactory = Callable[[str | None], AndroidRecordingBackend]


@dataclass
class _SessionRuntimeState:
    session: RecordingSession
    latest_frame: LiveViewFrame | None = None
    latest_manifest: RecordingAssetManifest | None = None
    recorded_events: list[RecordedInputEvent] | None = None
    forwarding_events: list[ForwardingEvent] | None = None
    timeline_entries: list[TimelineEntry] | None = None
    latest_observation: ObservationSnapshot | None = None
    worker: Thread | None = None
    stop_event: Event | None = None


class RecordingService:
    def __init__(
        self,
        *,
        store: RecordingStore | None = None,
        backend_factory: BackendFactory = AndroidRecordingBackend.connect,
        capture_interval_seconds: float = DEFAULT_CAPTURE_INTERVAL_SECONDS,
        stabilization_interval_seconds: float = DEFAULT_STABILIZATION_INTERVAL_SECONDS,
        stabilization_timeout_seconds: float = DEFAULT_STABILIZATION_TIMEOUT_SECONDS,
    ) -> None:
        self._store = store or RecordingStore()
        self._backend_factory = backend_factory
        self._capture_interval_seconds = capture_interval_seconds
        self._stabilization_interval_seconds = stabilization_interval_seconds
        self._stabilization_timeout_seconds = stabilization_timeout_seconds
        self._observation_capture = ObservationCaptureCoordinator(
            store=self._store,
            stabilization_interval_seconds=stabilization_interval_seconds,
            stabilization_timeout_seconds=stabilization_timeout_seconds,
        )
        # Runtime session state is intentionally process-local in A3B.
        # Disk assets remain durable for inspection/export, but are not used
        # to recover active sessions after process restart.
        self._sessions: dict[str, _SessionRuntimeState] = {}
        self._lock = Lock()
        self._analysis_runner: Callable[[dict[str, Any], Callable[[str, dict[str, Any]], None] | None], RecordingAnalysisResult] | None = None
        self._replay_runner: Callable[[str, RecordingSession, TestCase], RecordingReplayResult] | None = None

    def bind_analysis_runner(
        self,
        analysis_runner: Callable[[dict[str, Any], Callable[[str, dict[str, Any]], None] | None], RecordingAnalysisResult],
    ) -> None:
        self._analysis_runner = analysis_runner

    def bind_replay_runner(
        self,
        replay_runner: Callable[[str, RecordingSession, TestCase], RecordingReplayResult],
    ) -> None:
        self._replay_runner = replay_runner

    def create_session(
        self,
        *,
        app_target: AppTarget,
        device_ref: str | None = None,
        case_id: str | None = None,
    ) -> RecordingSession:
        session = self._store.create_session(
            app_target=app_target,
            device_ref=device_ref,
            case_id=case_id,
        )
        with self._lock:
            self._sessions[session.recording_id] = _SessionRuntimeState(
                session=session,
                recorded_events=[],
                forwarding_events=[],
                timeline_entries=[],
            )
        return session

    def begin_session(self, recording_id: str) -> RecordingSession:
        state = self._require_state(recording_id)
        if state.session.status != "created":
            raise RecordingSessionStateError(
                f"recording session '{recording_id}' cannot begin from status '{state.session.status}'"
            )

        stop_event = Event()
        try:
            backend = self._backend_factory(state.session.device_ref)
            if state.session.app_target.entry_identity:
                backend.app_start(state.session.app_target.entry_identity)
            frame = self._observation_capture.capture_frame(session=state.session, backend=backend, seq=1)
            initial_observation = self._observation_capture.persist_observation(
                session=state.session,
                backend=backend,
                observation_id=self._observation_capture.next_observation_id(state.latest_manifest),
                frame_seq=frame.seq,
                stabilized=True,
            )
        except Exception as exc:
            failed_session = state.session.model_copy(
                update={
                    "status": "failed",
                    "finished_at": now_iso(),
                    "failure_reason": str(exc),
                }
            )
            state.session = failed_session
            self._store.write_session(failed_session)
            raise

        started_session = state.session.model_copy(
            update={
                "status": "recording",
                "started_at": frame.captured_at,
                "latest_frame_seq": frame.seq,
                "failure_reason": None,
            }
        )
        manifest = self._store.read_manifest(started_session.asset_dir)
        state.session = started_session
        state.latest_frame = frame
        state.latest_manifest = manifest
        state.latest_observation = initial_observation
        state.stop_event = stop_event
        self._store.write_session(started_session)

        worker = Thread(
            target=self._capture_loop,
            name=f"recording-{recording_id}",
            args=(recording_id, backend, stop_event),
            daemon=True,
        )
        state.worker = worker
        worker.start()
        return started_session

    def get_session(self, recording_id: str) -> RecordingSession:
        return self._require_state(recording_id).session

    def get_live_frame(self, recording_id: str) -> LiveViewFrame | None:
        return self._require_state(recording_id).latest_frame

    def stop_session(self, recording_id: str) -> RecordingSession:
        return self._finish_session(recording_id, final_status="stopped")

    def cancel_session(self, recording_id: str) -> RecordingSession:
        return self._finish_session(recording_id, final_status="cancelled")

    def record_tap(self, recording_id: str, command: ObservedTapCommand) -> RecordedInputEvent:
        timeline_entry = self.record_interaction(recording_id, tap_to_interaction(command))
        state = self._require_state(recording_id)
        events = state.recorded_events or []
        for event in reversed(events):
            if event.event_id == timeline_entry.recording_event_id:
                return event
        raise RecordingSessionNotFoundError(
            f"recording event '{timeline_entry.recording_event_id}' was not found for recording '{recording_id}'"
        )

    def record_interaction(self, recording_id: str, command: RecordInteractionCommand) -> TimelineEntry:
        state = self._require_state(recording_id)
        if state.session.status != "recording":
            raise RecordingSessionStateError(
                f"recording session '{recording_id}' cannot record interaction from status '{state.session.status}'"
            )
        validate_record_interaction_contract(command)
        backend = self._backend_factory(state.session.device_ref)
        before_observation = state.latest_observation
        if before_observation is None:
            before_observation = self._observation_capture.persist_observation(
                session=state.session,
                backend=backend,
                observation_id=self._observation_capture.next_observation_id(state.latest_manifest),
                frame_seq=state.session.latest_frame_seq,
                stabilized=True,
            )
            state.latest_observation = before_observation
        forwarding_event = build_forwarding_event(
            recording_id=state.session.recording_id,
            command=command,
            next_index=len(state.forwarding_events or []) + 1,
        )
        manifest = self._store.append_forwarding_event(state.session, forwarding_event)
        after_observation = self._observation_capture.capture_stable_after_observation(
            session=state.session,
            backend=backend,
            latest_manifest=state.latest_manifest,
            latest_frame_seq=state.session.latest_frame_seq,
            stop_event=state.stop_event,
        )
        recording_event = build_recording_event(
            recording_id=state.session.recording_id,
            command=command,
            after_observation=after_observation,
            next_index=len(state.recorded_events or []) + 1,
        )
        manifest = self._store.append_recording_event(state.session, recording_event)
        entry = TimelineEntry(
            entry_id=f"entry_{len(state.timeline_entries or []) + 1:06d}",
            recording_id=recording_id,
            seq=len(state.timeline_entries or []) + 1,
            kind=command.kind,
            summary=recording_event.summary,
            forwarding_event_id=forwarding_event.forwarding_event_id,
            recording_event_id=recording_event.event_id,
            before_observation_id=before_observation.observation_id,
            after_observation_id=after_observation.observation_id,
            after_stabilized=after_observation.stabilized,
        )
        manifest = self._store.append_timeline_entry(state.session, entry)
        state.latest_manifest = manifest
        if state.forwarding_events is None:
            state.forwarding_events = []
        if state.recorded_events is None:
            state.recorded_events = []
        if state.timeline_entries is None:
            state.timeline_entries = []
        state.forwarding_events.append(forwarding_event)
        state.recorded_events.append(recording_event)
        state.timeline_entries.append(entry)
        state.latest_observation = after_observation
        return entry

    def list_recorded_events(
        self,
        recording_id: str,
        *,
        after_seq: int = 0,
        limit: int = 100,
    ) -> list[RecordedInputEvent]:
        state = self._require_state(recording_id)
        events = state.recorded_events or []
        return events[after_seq : after_seq + limit]

    def list_timeline(
        self,
        recording_id: str,
        *,
        after_seq: int = 0,
        limit: int = 100,
    ) -> list[TimelineEntry]:
        state = self._require_state(recording_id)
        entries = state.timeline_entries or []
        return entries[after_seq : after_seq + limit]

    def get_observation(self, recording_id: str, observation_id: str) -> ObservationSnapshot:
        state = self._require_state(recording_id)
        if state.latest_observation and state.latest_observation.observation_id == observation_id:
            return state.latest_observation
        return self._store.read_observation(state.session.asset_dir, observation_id)

    def load_recording_assets(self, recording_id: str) -> dict[str, Any]:
        return build_recording_asset_bundle(self._store, recording_id=recording_id)

    def load_analysis_result(self, recording_id: str) -> RecordingAnalysisResult | None:
        recording_dir = self._store.find_recording_dir(recording_id)
        return self._store.read_analysis_result(recording_dir)

    def load_exported_test_case(self, recording_id: str) -> TestCase | None:
        recording_dir = self._store.find_recording_dir(recording_id)
        return self._store.read_test_case(recording_dir)

    def load_export_manifest(self, recording_id: str) -> RecordingCaseExport | None:
        recording_dir = self._store.find_recording_dir(recording_id)
        return self._store.read_export_manifest(recording_dir)

    def analyze_recording(
        self,
        recording_id: str,
        *,
        progress_callback: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> RecordingAnalysisResult:
        return self.ensure_analysis(recording_id, progress_callback=progress_callback)

    def ensure_analysis(
        self,
        recording_id: str,
        *,
        progress_callback: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> RecordingAnalysisResult:
        bundle = self.load_recording_assets(recording_id)
        session_payload = cast(dict[str, Any], bundle["session"])
        status = str(session_payload.get("status", "unknown"))
        cached = self.load_analysis_result(recording_id)
        if cached is not None and cached.status == "completed":
            return cached
        if status == "failed":
            analysis = RecordingAnalysisResult(
                recording_id=recording_id,
                status="failed",
                failure_reason=str(session_payload.get("failure_reason") or "recording session failed"),
                source_summary=cast(str | None, bundle.get("source_summary")),
            )
            self._store.write_analysis_result(self._store.find_recording_dir(recording_id), analysis)
            return analysis
        if status not in {"stopped", "cancelled"}:
            raise RecordingSessionStateError(
                f"recording session '{recording_id}' cannot be analyzed from status '{status}'"
            )
        if self._analysis_runner is None:
            raise RuntimeError("recording analysis runner is unavailable")
        analysis = self._analysis_runner(bundle, progress_callback)
        self._store.write_analysis_result(self._store.find_recording_dir(recording_id), analysis)
        return analysis

    def export_case(self, recording_id: str) -> RecordingCaseExport:
        _, export_result = self.ensure_export(recording_id)
        return export_result

    def ensure_export(self, recording_id: str) -> tuple[RecordingAnalysisResult, RecordingCaseExport]:
        recording_dir = self._store.find_recording_dir(recording_id)
        existing_analysis = self.ensure_analysis(recording_id)
        existing_export = self._store.read_export_manifest(recording_dir)
        existing_case = self._store.read_test_case(recording_dir)
        if (
            existing_export is not None
            and existing_case is not None
            and existing_export.case_path.exists()
            and existing_export.analysis_path.exists()
        ):
            try:
                validate_case_definition(
                    existing_case,
                    context=f"cached recording export for '{recording_id}'",
                )
                return existing_analysis, existing_export
            except InvalidCaseDefinitionError:
                pass
        export_result = export_analysis_case(self._store, recording_id=recording_id, analysis=existing_analysis)
        return existing_analysis, export_result

    def replay_case(self, recording_id: str) -> RecordingReplayResult:
        if self._replay_runner is None:
            raise RuntimeError("recording replay runner is unavailable")
        recording_dir = self._store.find_recording_dir(recording_id)
        analysis, _ = self.ensure_export(recording_id)
        test_case = analysis.test_case or self._store.read_test_case(recording_dir)
        if test_case is None:
            raise RuntimeError("recording replay requires an exported canonical test case")
        session = self._store.read_session(recording_dir)
        replay_result = self._replay_runner(recording_id, session, test_case)
        self._store.write_replay_manifest(recording_dir, replay_result)
        return replay_result

    def diagnose(self) -> RecordingRuntimeHealth:
        assets_root = ensure_recording_assets_home()
        details = {"assets_root": str(assets_root)}
        try:
            assets_root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return RecordingRuntimeHealth(
                runtime_id="local",
                status="error",
                message="recording assets root is not writable",
                details={**details, "error": str(exc)},
            )
        return RecordingRuntimeHealth(
            runtime_id="local",
            status="ok",
            message="recording local runtime is available",
            details=details,
        )

    def _finish_session(self, recording_id: str, *, final_status: str) -> RecordingSession:
        state = self._require_state(recording_id)
        if state.session.status not in {"recording", "failed"}:
            raise RecordingSessionStateError(
                f"recording session '{recording_id}' cannot transition from '{state.session.status}' "
                f"to '{final_status}'"
            )

        if state.stop_event is not None:
            state.stop_event.set()
        if state.worker is not None:
            state.worker.join(timeout=max(self._capture_interval_seconds * 2, 0.2))

        final_session = state.session.model_copy(
            update={
                "status": final_status if state.session.status != "failed" else "failed",
                "finished_at": now_iso(),
            }
        )
        state.session = final_session
        self._store.write_session(final_session)
        return final_session

    def _capture_loop(
        self,
        recording_id: str,
        backend: AndroidRecordingBackend,
        stop_event: Event,
    ) -> None:
        while not stop_event.wait(self._capture_interval_seconds):
            state = self._require_state(recording_id)
            next_seq = (state.session.latest_frame_seq or 0) + 1
            try:
                frame = self._observation_capture.capture_frame(session=state.session, backend=backend, seq=next_seq)
            except Exception as exc:
                failed_session = state.session.model_copy(
                    update={
                        "status": "failed",
                        "finished_at": now_iso(),
                        "failure_reason": str(exc),
                    }
                )
                state.session = failed_session
                self._store.write_session(failed_session)
                stop_event.set()
                return

            updated_session = state.session.model_copy(update={"latest_frame_seq": frame.seq})
            state.session = updated_session
            state.latest_frame = frame
            state.latest_manifest = self._store.read_manifest(updated_session.asset_dir)
            self._store.write_session(updated_session)

    def _require_state(self, recording_id: str) -> _SessionRuntimeState:
        with self._lock:
            state = self._sessions.get(recording_id)
        if state is None:
            raise RecordingSessionNotFoundError(f"recording session '{recording_id}' was not found")
        return state
