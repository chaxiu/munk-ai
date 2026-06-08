from __future__ import annotations

import hashlib
from dataclasses import dataclass
from threading import Event, Lock, Thread
from time import monotonic
from typing import Any, Callable, cast

from munk.app import AppTarget
from munk.recording import (
    ForwardingAck,
    ForwardingEvent,
    ForwardingStep,
    LiveViewFrame,
    ObservationSnapshot,
    ObservedTapCommand,
    RecordedCurrentAppState,
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
from munk.testing import TestCase

from .analysis import build_recording_asset_bundle
from .android_backend import AndroidRecordingBackend
from .exporter import export_analysis_case
from .paths import ensure_recording_assets_home
from .store import RecordingStore

DEFAULT_CAPTURE_INTERVAL_SECONDS = 1.0
DEFAULT_STABILIZATION_INTERVAL_SECONDS = 0.2
DEFAULT_STABILIZATION_TIMEOUT_SECONDS = 2.0


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
        backend_factory=AndroidRecordingBackend.connect,
        capture_interval_seconds: float = DEFAULT_CAPTURE_INTERVAL_SECONDS,
        stabilization_interval_seconds: float = DEFAULT_STABILIZATION_INTERVAL_SECONDS,
        stabilization_timeout_seconds: float = DEFAULT_STABILIZATION_TIMEOUT_SECONDS,
    ) -> None:
        self._store = store or RecordingStore()
        self._backend_factory = backend_factory
        self._capture_interval_seconds = capture_interval_seconds
        self._stabilization_interval_seconds = stabilization_interval_seconds
        self._stabilization_timeout_seconds = stabilization_timeout_seconds
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
            frame = self._capture_frame(session=state.session, backend=backend, seq=1)
            initial_observation = self._persist_observation(
                session=state.session,
                backend=backend,
                observation_id=self._next_observation_id(state),
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
        timeline_entry = self.record_interaction(recording_id, self._tap_to_interaction(command))
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
            before_observation = self._persist_observation(
                session=state.session,
                backend=backend,
                observation_id=self._next_observation_id(state),
                frame_seq=state.session.latest_frame_seq,
                stabilized=True,
            )
            state.latest_observation = before_observation
        forwarding_event = self._build_forwarding_event(state.session, command, state)
        manifest = self._store.append_forwarding_event(state.session, forwarding_event)
        after_observation = self._capture_stable_after_observation(
            state=state,
            backend=backend,
        )
        recording_event = self._build_recording_event(
            session=state.session,
            command=command,
            after_observation=after_observation,
            state=state,
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
            return existing_analysis, existing_export
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
                frame = self._capture_frame(session=state.session, backend=backend, seq=next_seq)
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

    def _capture_frame(
        self,
        *,
        session: RecordingSession,
        backend: AndroidRecordingBackend,
        seq: int,
    ) -> LiveViewFrame:
        image = backend.screenshot_bgr()
        current = backend.app_current()
        entry_identity = current.entry_identity
        activity_name = current.activity_name
        frame = LiveViewFrame(
            recording_id=session.recording_id,
            seq=seq,
            image_path=self._store.frame_image_path(session.asset_dir, seq),
            width=int(image.shape[1]),
            height=int(image.shape[0]),
            entry_identity=entry_identity,
            activity_name=activity_name,
        )
        self._store.write_frame(session, frame, image)
        return frame

    def _capture_stable_after_observation(
        self,
        *,
        state: _SessionRuntimeState,
        backend: AndroidRecordingBackend,
    ) -> ObservationSnapshot:
        deadline = monotonic() + self._stabilization_timeout_seconds
        last_candidate: _ObservationCandidate | None = None
        stable_hits = 0
        while True:
            candidate = self._capture_observation_candidate(backend=backend)
            if last_candidate is not None and candidate.observation_hash == last_candidate.observation_hash:
                stable_hits += 1
            else:
                stable_hits = 1
            last_candidate = candidate
            if stable_hits >= 2:
                return self._persist_observation_from_candidate(
                    session=state.session,
                    candidate=candidate,
                    observation_id=self._next_observation_id(state),
                    frame_seq=state.session.latest_frame_seq,
                    stabilized=True,
                )
            if monotonic() >= deadline:
                return self._persist_observation_from_candidate(
                    session=state.session,
                    candidate=candidate,
                    observation_id=self._next_observation_id(state),
                    frame_seq=state.session.latest_frame_seq,
                    stabilized=False,
                )
            state.stop_event.wait(self._stabilization_interval_seconds) if state.stop_event else None

    def _persist_observation(
        self,
        *,
        session: RecordingSession,
        backend: AndroidRecordingBackend,
        observation_id: str,
        frame_seq: int | None,
        stabilized: bool,
    ) -> ObservationSnapshot:
        candidate = self._capture_observation_candidate(backend=backend)
        return self._persist_observation_from_candidate(
            session=session,
            candidate=candidate,
            observation_id=observation_id,
            frame_seq=frame_seq,
            stabilized=stabilized,
        )

    def _persist_observation_from_candidate(
        self,
        *,
        session: RecordingSession,
        candidate: "_ObservationCandidate",
        observation_id: str,
        frame_seq: int | None,
        stabilized: bool,
    ) -> ObservationSnapshot:
        observation = ObservationSnapshot(
            observation_id=observation_id,
            recording_id=session.recording_id,
            image_path=self._store.observation_image_path(session.asset_dir, observation_id),
            metadata_path=self._store.observation_meta_path(session.asset_dir, observation_id),
            ui_tree_path=self._store.observation_tree_path(session.asset_dir, observation_id)
            if candidate.ui_tree_text is not None
            else None,
            entry_identity=candidate.entry_identity,
            surface_identity=candidate.surface_identity,
            current_app_state=candidate.current_app_state,
            frame_seq=frame_seq,
            tree_available=candidate.ui_tree_text is not None,
            ui_tree_hash=candidate.ui_tree_hash,
            screenshot_hash=candidate.screenshot_hash,
            stabilized=stabilized,
        )
        self._store.write_observation(
            session,
            observation,
            candidate.image,
            metadata=observation.model_dump(mode="json"),
            ui_tree_text=candidate.ui_tree_text,
        )
        return observation

    def _capture_observation_candidate(self, *, backend: AndroidRecordingBackend) -> "_ObservationCandidate":
        image = backend.screenshot_bgr()
        current = backend.app_current()
        entry_identity = current.entry_identity
        surface_identity = current.surface_identity
        observation_tree = backend.capture_observation_tree()
        ui_tree_text = observation_tree.payload if observation_tree is not None else None
        ui_tree_hash = _hash_text(cast(str | None, ui_tree_text)) if ui_tree_text is not None else None
        screenshot_hash = _hash_bytes(image.tobytes())
        observation_hash = f"{entry_identity}|{surface_identity}|{ui_tree_hash or screenshot_hash}"
        current_app_state = RecordedCurrentAppState(
            platform=current.platform,
            entry_identity=entry_identity,
            surface_identity=surface_identity,
            url=current.url,
            title=current.title,
            load_state=current.load_state,
            raw=_trim_current_app_state_raw(cast(dict[str, object], current.raw)),
        )
        return _ObservationCandidate(
            image=image,
            entry_identity=entry_identity,
            surface_identity=surface_identity,
            current_app_state=current_app_state,
            ui_tree_text=ui_tree_text,
            ui_tree_hash=ui_tree_hash,
            screenshot_hash=screenshot_hash,
            observation_hash=observation_hash,
        )

    @staticmethod
    def _next_observation_id(state: _SessionRuntimeState) -> str:
        next_index = (state.latest_manifest.observation_count if state.latest_manifest is not None else 0) + 1
        return f"obs_{next_index:06d}"

    @staticmethod
    def _tap_to_interaction(command: ObservedTapCommand) -> RecordInteractionCommand:
        x_ratio = command.x_ratio if command.x_ratio is not None else round(command.x / command.width, 6)
        y_ratio = command.y_ratio if command.y_ratio is not None else round(command.y / command.height, 6)
        steps = [
            ForwardingStep(seq=1, step_kind="pointer_down", payload={"x": command.x, "y": command.y}),
            ForwardingStep(seq=2, step_kind="pointer_up", payload={"x": command.x, "y": command.y}),
        ]
        return RecordInteractionCommand(
            client_command_id=f"tap-{command.x}-{command.y}",
            kind="click",
            forwarding_ack=ForwardingAck(
                kind="pointer",
                dispatched_at=now_iso(),
                payload={
                    "x": command.x,
                    "y": command.y,
                    "width": command.width,
                    "height": command.height,
                    "x_ratio": x_ratio,
                    "y_ratio": y_ratio,
                    "source": command.source,
                },
                steps=steps,
            ),
            payload={
                "x": command.x,
                "y": command.y,
                "width": command.width,
                "height": command.height,
                "x_ratio": x_ratio,
                "y_ratio": y_ratio,
            },
            source=command.source,
        )

    @staticmethod
    def _build_forwarding_event(
        session: RecordingSession,
        command: RecordInteractionCommand,
        state: _SessionRuntimeState,
    ) -> ForwardingEvent:
        next_index = len(state.forwarding_events or []) + 1
        return ForwardingEvent(
            forwarding_event_id=f"fwd_{next_index:06d}",
            recording_id=session.recording_id,
            client_command_id=command.client_command_id,
            kind=command.forwarding_ack.kind,
            dispatched_at=command.forwarding_ack.dispatched_at,
            ack_at=command.forwarding_ack.ack_at,
            payload=command.forwarding_ack.payload,
            steps=command.forwarding_ack.steps,
            device_result=command.forwarding_ack.device_result,
        )

    @staticmethod
    def _build_recording_event(
        *,
        session: RecordingSession,
        command: RecordInteractionCommand,
        after_observation: ObservationSnapshot,
        state: _SessionRuntimeState,
    ) -> RecordedInputEvent:
        next_index = len(state.recorded_events or []) + 1
        return RecordedInputEvent(
            event_id=f"evt_{next_index:06d}",
            recording_id=session.recording_id,
            kind=command.kind,
            summary=_build_summary(command),
            source=command.source,
            payload={
                **command.payload,
                "client_command_id": command.client_command_id,
                "after_observation_id": after_observation.observation_id,
                "entry_identity": after_observation.entry_identity,
                "surface_identity": after_observation.surface_identity,
            },
        )

    def _require_state(self, recording_id: str) -> _SessionRuntimeState:
        with self._lock:
            state = self._sessions.get(recording_id)
        if state is None:
            raise RecordingSessionNotFoundError(f"recording session '{recording_id}' was not found")
        return state


@dataclass
class _ObservationCandidate:
    image: object
    entry_identity: str | None
    surface_identity: str | None
    current_app_state: RecordedCurrentAppState | None
    ui_tree_text: str | None
    ui_tree_hash: str | None
    screenshot_hash: str
    observation_hash: str


def _hash_text(value: str | None) -> str | None:
    if value is None:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _hash_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _trim_current_app_state_raw(raw: dict[str, object]) -> dict[str, object]:
    allowed_keys = {"url", "title", "load_state", "origin", "surface_identity"}
    return {key: value for key, value in raw.items() if key in allowed_keys and value is not None}


def _build_summary(command: RecordInteractionCommand) -> str:
    payload = command.payload or command.forwarding_ack.payload
    if command.kind == "click":
        return f"click at ({payload.get('x')}, {payload.get('y')})"
    if command.kind == "swipe":
        return (
            f"swipe from ({payload.get('start_x')}, {payload.get('start_y')}) "
            f"to ({payload.get('end_x')}, {payload.get('end_y')})"
        )
    if command.kind == "input":
        return f"input text: {payload.get('text', '')}"
    return "press back"
