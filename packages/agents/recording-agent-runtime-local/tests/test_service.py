from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from munk.app import AndroidAppIdentity, AppTarget
from munk.device import CurrentAppState
from munk.perception import ObservationTree
from munk.recording import (
    ForwardingAck,
    ForwardingStep,
    ObservedTapCommand,
    RecordingAnalysisResult,
    RecordingInteractionContractError,
    RecordingReplayResult,
    RecordingSessionNotFoundError,
    RecordingSessionStateError,
    RecordInteractionCommand,
)
from munk.testing import TestCase
from munk_recording_local.service import RecordingService
from munk_recording_local.store import RecordingStore


def build_app_target(app_id: str = "demo-app", package_name: str = "com.demo.app") -> AppTarget:
    return AppTarget(
        app_id=app_id,
        platform="android",
        android=AndroidAppIdentity(package_name=package_name),
    )


class FakeBackend:
    def __init__(self) -> None:
        self.started_entry_identities: list[str] = []

    def app_start(self, entry_identity: str) -> None:
        self.started_entry_identities.append(entry_identity)

    def screenshot_bgr(self):
        return np.zeros((6, 5, 3), dtype=np.uint8)

    def app_current(self) -> CurrentAppState:
        return CurrentAppState(
            platform="android",
            entry_identity="com.demo.app",
            activity_name=".MainActivity",
            surface_identity="com.demo.app/.MainActivity",
        )

    def capture_observation_tree(self) -> ObservationTree | None:
        return ObservationTree(
            source_type="android_uixml",
            content_type="xml",
            payload=(
                '<hierarchy><node class="android.widget.FrameLayout" bounds="[0,0][100,200]">'
                '<node class="android.widget.TextView" text="Demo Task" resource-id="com.demo:id/task_title" '
                'content-desc="Demo Task" bounds="[10,20][90,60]" clickable="true" enabled="true" />'
                "</node></hierarchy>"
            ),
        )


class ChangingTreeBackend(FakeBackend):
    def __init__(self) -> None:
        super().__init__()
        self._tree_call_count = 0

    def capture_observation_tree(self) -> ObservationTree | None:
        self._tree_call_count += 1
        text = "Demo Task" if self._tree_call_count == 1 else "Detail"
        return ObservationTree(
            source_type="android_uixml",
            content_type="xml",
            payload=(
                '<hierarchy><node class="android.widget.FrameLayout" bounds="[0,0][100,200]">'
                f'<node class="android.widget.TextView" text="{text}" resource-id="com.demo:id/task_title" '
                f'content-desc="{text}" bounds="[10,20][90,60]" clickable="true" enabled="true" />'
                "</node></hierarchy>"
            ),
        )


def test_create_begin_stop_flow(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MUNK_HOME", str(tmp_path))
    backend = FakeBackend()
    service = RecordingService(
        backend_factory=lambda serial: backend,
        capture_interval_seconds=60.0,
    )
    session = service.create_session(app_target=build_app_target(), device_ref=None)

    started = service.begin_session(session.recording_id)
    stopped = service.stop_session(session.recording_id)

    assert started.status == "recording"
    assert started.latest_frame_seq == 1
    assert service.get_live_frame(session.recording_id) is not None
    assert stopped.status == "stopped"
    assert backend.started_entry_identities == ["com.demo.app"]
    store = RecordingStore()
    observation = store.read_observation(session.asset_dir, "obs_000001")
    assert observation.surface_identity == "com.demo.app/.MainActivity"
    assert observation.current_app_state is not None
    assert observation.current_app_state.surface_identity == "com.demo.app/.MainActivity"


def test_create_begin_cancel_flow(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MUNK_HOME", str(tmp_path))
    service = RecordingService(
        backend_factory=lambda serial: FakeBackend(),
        capture_interval_seconds=60.0,
    )
    session = service.create_session(app_target=build_app_target(), device_ref=None)

    service.begin_session(session.recording_id)
    cancelled = service.cancel_session(session.recording_id)

    assert cancelled.status == "cancelled"
    assert cancelled.finished_at is not None


def test_begin_failure_marks_session_failed(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MUNK_HOME", str(tmp_path))
    service = RecordingService(
        backend_factory=lambda serial: (_ for _ in ()).throw(RuntimeError("connect failed")),
        capture_interval_seconds=60.0,
    )
    session = service.create_session(app_target=build_app_target(), device_ref=None)

    with pytest.raises(RuntimeError, match="connect failed"):
        service.begin_session(session.recording_id)

    failed = service.get_session(session.recording_id)
    assert failed.status == "failed"
    assert failed.failure_reason == "connect failed"


def test_invalid_state_transition_raises(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MUNK_HOME", str(tmp_path))
    service = RecordingService(
        backend_factory=lambda serial: FakeBackend(),
        capture_interval_seconds=60.0,
    )
    session = service.create_session(app_target=build_app_target(), device_ref=None)

    with pytest.raises(RecordingSessionStateError):
        service.stop_session(session.recording_id)


def test_record_tap_appends_event_and_evidence(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MUNK_HOME", str(tmp_path))
    backend = FakeBackend()
    service = RecordingService(
        backend_factory=lambda serial: backend,
        capture_interval_seconds=60.0,
    )
    session = service.create_session(app_target=build_app_target(), device_ref=None)
    service.begin_session(session.recording_id)

    event = service.record_tap(
        session.recording_id,
        ObservedTapCommand(x=2, y=3, width=5, height=6),
    )
    events = service.list_recorded_events(session.recording_id)

    assert event.kind == "click"
    assert len(events) == 1
    assert events[0].event_id == "evt_000001"
    assert (session.asset_dir / "events" / "recording.jsonl").is_file()
    assert (session.asset_dir / "timeline" / "timeline.jsonl").is_file()
    assert (session.asset_dir / "observations" / "obs_000001" / "screen.png").is_file()


def test_record_interaction_preserves_pointer_forwarding_kind(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MUNK_HOME", str(tmp_path))
    backend = FakeBackend()
    service = RecordingService(
        backend_factory=lambda serial: backend,
        capture_interval_seconds=60.0,
    )
    session = service.create_session(app_target=build_app_target(), device_ref=None)
    service.begin_session(session.recording_id)

    entry = service.record_interaction(
        session.recording_id,
        RecordInteractionCommand(
            client_command_id="cmd-1",
            kind="click",
            forwarding_ack=ForwardingAck(
                kind="pointer",
                payload={"x": 2, "y": 3, "width": 5, "height": 6},
                steps=[
                        ForwardingStep(seq=1, step_kind="pointer_down", payload={"x": 2, "y": 3}),
                        ForwardingStep(seq=2, step_kind="pointer_up", payload={"x": 2, "y": 3}),
                ],
                device_result={"ok": True},
            ),
            payload={"x": 2, "y": 3, "width": 5, "height": 6},
        ),
    )

    assert entry.kind == "click"
    forwarding_path = session.asset_dir / "events" / "forwarding.jsonl"
    assert forwarding_path.is_file()
    assert '"kind":"pointer"' in forwarding_path.read_text(encoding="utf-8")


def test_record_interaction_rejects_invalid_interaction_contract(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MUNK_HOME", str(tmp_path))
    backend = FakeBackend()
    service = RecordingService(
        backend_factory=lambda serial: backend,
        capture_interval_seconds=60.0,
    )
    session = service.create_session(app_target=build_app_target(), device_ref=None)
    service.begin_session(session.recording_id)

    with pytest.raises(RecordingInteractionContractError, match="requires forwarding_ack.kind='pointer'"):
        service.record_interaction(
            session.recording_id,
            RecordInteractionCommand(
                client_command_id="cmd-1",
                kind="click",
                forwarding_ack=ForwardingAck(
                    kind="input",
                    payload={"text": "hello"},
                    steps=[
                        ForwardingStep(seq=1, step_kind="text_inject", payload={"text": "hello"}),
                    ],
                    device_result={"ok": True},
                ),
                payload={"x": 2, "y": 3, "width": 5, "height": 6},
            ),
        )


def test_recording_sessions_remain_process_local_even_when_assets_exist(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MUNK_HOME", str(tmp_path))
    service = RecordingService(
        backend_factory=lambda serial: FakeBackend(),
        capture_interval_seconds=60.0,
    )
    session = service.create_session(app_target=build_app_target(), device_ref=None)

    restarted_service = RecordingService(
        backend_factory=lambda serial: FakeBackend(),
        capture_interval_seconds=60.0,
    )

    with pytest.raises(RecordingSessionNotFoundError, match=session.recording_id):
        restarted_service.get_session(session.recording_id)


def test_analyze_and_export_stopped_recording(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MUNK_HOME", str(tmp_path))
    backend = FakeBackend()
    service = RecordingService(
        backend_factory=lambda serial: backend,
        capture_interval_seconds=60.0,
    )
    session = service.create_session(app_target=build_app_target(), device_ref=None, case_id="case-1")
    service.begin_session(session.recording_id)
    service.record_interaction(
        session.recording_id,
        RecordInteractionCommand(
            client_command_id="cmd-1",
            kind="click",
            forwarding_ack=ForwardingAck(
                kind="pointer",
                payload={"x": 2, "y": 3, "width": 5, "height": 6},
                steps=[
                    ForwardingStep(seq=1, step_kind="pointer_down", payload={"x": 2, "y": 3}),
                    ForwardingStep(seq=2, step_kind="pointer_up", payload={"x": 2, "y": 3}),
                ],
            ),
            payload={"x": 2, "y": 3, "width": 5, "height": 6},
        ),
    )
    service.stop_session(session.recording_id)
    service.bind_analysis_runner(
        lambda bundle, progress_callback=None: RecordingAnalysisResult(  # noqa: ARG005
            recording_id=str(bundle["recording_id"]),
            status="completed",
            test_case=TestCase(
                case_id="case-1",
                title="Generated Case",
                intent="Verify the recorded flow",
                procedure=["Tap generated button"],
                expected=["The visible state changes as expected"],
                runner_goal="Replay the recorded flow and verify the visible state change",
            ),
            export_ready=True,
        )
    )

    analysis = service.analyze_recording(session.recording_id)
    export_result = service.export_case(session.recording_id)

    assert analysis.status == "completed"
    assert analysis.test_case is not None
    assert export_result.case_path.is_file()
    assert export_result.analysis_path.is_file()


def test_load_recording_assets_includes_compact_tree_excerpt_and_diff(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MUNK_HOME", str(tmp_path))
    backend = FakeBackend()
    service = RecordingService(
        backend_factory=lambda serial: backend,
        capture_interval_seconds=60.0,
    )
    session = service.create_session(app_target=build_app_target(), device_ref=None, case_id="case-1")
    service.begin_session(session.recording_id)
    service.record_interaction(
        session.recording_id,
        RecordInteractionCommand(
            client_command_id="cmd-1",
            kind="click",
            forwarding_ack=ForwardingAck(
                kind="pointer",
                payload={"x": 2, "y": 3, "width": 5, "height": 6},
                steps=[
                    ForwardingStep(seq=1, step_kind="pointer_down", payload={"x": 2, "y": 3}),
                    ForwardingStep(seq=2, step_kind="pointer_up", payload={"x": 2, "y": 3}),
                ],
            ),
            payload={"x": 2, "y": 3, "width": 5, "height": 6, "label": "Demo Task"},
        ),
    )
    service.stop_session(session.recording_id)

    bundle = service.load_recording_assets(session.recording_id)
    step = bundle["steps"][0]
    before_excerpt = step["before_screenshot"]["compact_tree_excerpt"]
    tree_diff = step["tree_diff"]

    assert before_excerpt["node_count"] >= 1
    assert before_excerpt["compact_nodes"][0]["node_id"] == "node_0001"
    assert tree_diff["summary"] == "no compact tree change"
    assert tree_diff["added_nodes"] == []
    assert tree_diff["changed_nodes"] == []


def test_load_recording_assets_builds_tree_diff_for_changed_nodes(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MUNK_HOME", str(tmp_path))
    backend = ChangingTreeBackend()
    service = RecordingService(
        backend_factory=lambda serial: backend,
        capture_interval_seconds=60.0,
    )
    session = service.create_session(app_target=build_app_target(), device_ref=None, case_id="case-1")
    service.begin_session(session.recording_id)
    service.record_interaction(
        session.recording_id,
        RecordInteractionCommand(
            client_command_id="cmd-1",
            kind="click",
            forwarding_ack=ForwardingAck(
                kind="pointer",
                payload={"x": 2, "y": 3, "width": 5, "height": 6},
                steps=[
                    ForwardingStep(seq=1, step_kind="pointer_down", payload={"x": 2, "y": 3}),
                    ForwardingStep(seq=2, step_kind="pointer_up", payload={"x": 2, "y": 3}),
                ],
            ),
            payload={"x": 2, "y": 3, "width": 5, "height": 6, "label": "Demo Task"},
        ),
    )
    service.stop_session(session.recording_id)

    bundle = service.load_recording_assets(session.recording_id)
    tree_diff = bundle["steps"][0]["tree_diff"]

    assert "nodes~1" in tree_diff["summary"]
    assert len(tree_diff["changed_nodes"]) == 1
    assert tree_diff["changed_nodes"][0]["changes"]["text"] == {"before": "Demo Task", "after": "Detail"}


def test_ensure_analysis_reuses_cached_result(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MUNK_HOME", str(tmp_path))
    backend = FakeBackend()
    service = RecordingService(
        backend_factory=lambda serial: backend,
        capture_interval_seconds=60.0,
    )
    session = service.create_session(app_target=build_app_target(), device_ref=None, case_id="case-1")
    service.begin_session(session.recording_id)
    service.record_interaction(
        session.recording_id,
        RecordInteractionCommand(
            client_command_id="cmd-1",
            kind="click",
            forwarding_ack=ForwardingAck(
                kind="pointer",
                payload={"x": 2, "y": 3, "width": 5, "height": 6},
                steps=[
                    ForwardingStep(seq=1, step_kind="pointer_down", payload={"x": 2, "y": 3}),
                    ForwardingStep(seq=2, step_kind="pointer_up", payload={"x": 2, "y": 3}),
                ],
            ),
            payload={"x": 2, "y": 3, "width": 5, "height": 6},
        ),
    )
    service.stop_session(session.recording_id)
    analysis_calls = 0

    def analysis_runner(bundle: dict[str, object], progress_callback=None) -> RecordingAnalysisResult:  # noqa: ANN001
        _ = progress_callback
        nonlocal analysis_calls
        analysis_calls += 1
        return RecordingAnalysisResult(
            recording_id=str(bundle["recording_id"]),
            status="completed",
            test_case=TestCase(
                case_id="case-1",
                title="Generated Case",
                intent="Verify the recorded flow",
                procedure=["Tap generated button"],
                expected=["The visible state changes as expected"],
                runner_goal="Replay the recorded flow and verify the visible state change",
            ),
            export_ready=True,
        )

    service.bind_analysis_runner(analysis_runner)

    first = service.ensure_analysis(session.recording_id)
    second = service.ensure_analysis(session.recording_id)

    assert first.status == "completed"
    assert second.status == "completed"
    assert analysis_calls == 1


def test_ensure_export_reuses_existing_manifest(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MUNK_HOME", str(tmp_path))
    backend = FakeBackend()
    service = RecordingService(
        backend_factory=lambda serial: backend,
        capture_interval_seconds=60.0,
    )
    session = service.create_session(app_target=build_app_target(), device_ref=None, case_id="case-1")
    service.begin_session(session.recording_id)
    service.record_interaction(
        session.recording_id,
        RecordInteractionCommand(
            client_command_id="cmd-1",
            kind="click",
            forwarding_ack=ForwardingAck(
                kind="pointer",
                payload={"x": 2, "y": 3, "width": 5, "height": 6},
                steps=[
                    ForwardingStep(seq=1, step_kind="pointer_down", payload={"x": 2, "y": 3}),
                    ForwardingStep(seq=2, step_kind="pointer_up", payload={"x": 2, "y": 3}),
                ],
            ),
            payload={"x": 2, "y": 3, "width": 5, "height": 6},
        ),
    )
    service.stop_session(session.recording_id)
    analysis_calls = 0

    def analysis_runner(bundle: dict[str, object], progress_callback=None) -> RecordingAnalysisResult:  # noqa: ANN001
        _ = progress_callback
        nonlocal analysis_calls
        analysis_calls += 1
        return RecordingAnalysisResult(
            recording_id=str(bundle["recording_id"]),
            status="completed",
            test_case=TestCase(
                case_id="case-1",
                title="Generated Case",
                intent="Verify the recorded flow",
                procedure=["Tap generated button"],
                expected=["The visible state changes as expected"],
                runner_goal="Replay the recorded flow and verify the visible state change",
            ),
            export_ready=True,
        )

    service.bind_analysis_runner(analysis_runner)

    first = service.export_case(session.recording_id)
    second = service.export_case(session.recording_id)

    assert first.case_path.is_file()
    assert second.case_path.is_file()
    assert first.exported_at == second.exported_at
    assert analysis_calls == 1


def test_ensure_analysis_retries_after_cached_failure(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MUNK_HOME", str(tmp_path))
    backend = FakeBackend()
    service = RecordingService(
        backend_factory=lambda serial: backend,
        capture_interval_seconds=60.0,
    )
    session = service.create_session(app_target=build_app_target(), device_ref=None, case_id="case-1")
    service.begin_session(session.recording_id)
    service.record_interaction(
        session.recording_id,
        RecordInteractionCommand(
            client_command_id="cmd-1",
            kind="click",
            forwarding_ack=ForwardingAck(
                kind="pointer",
                payload={"x": 2, "y": 3, "width": 5, "height": 6},
                steps=[
                    ForwardingStep(seq=1, step_kind="pointer_down", payload={"x": 2, "y": 3}),
                    ForwardingStep(seq=2, step_kind="pointer_up", payload={"x": 2, "y": 3}),
                ],
            ),
            payload={"x": 2, "y": 3, "width": 5, "height": 6},
        ),
    )
    service.stop_session(session.recording_id)
    analysis_calls = 0

    def analysis_runner(bundle: dict[str, object], progress_callback=None) -> RecordingAnalysisResult:  # noqa: ANN001
        _ = progress_callback
        nonlocal analysis_calls
        analysis_calls += 1
        if analysis_calls == 1:
            return RecordingAnalysisResult(
                recording_id=str(bundle["recording_id"]),
                status="failed",
                failure_reason="The next request would exceed the request_limit of 50",
                export_ready=False,
            )
        return RecordingAnalysisResult(
            recording_id=str(bundle["recording_id"]),
            status="completed",
            test_case=TestCase(
                case_id="case-1",
                title="Generated Case",
                intent="Verify the recorded flow",
                procedure=["Tap generated button"],
                expected=["The visible state changes as expected"],
                runner_goal="Replay the recorded flow and verify the visible state change",
            ),
            export_ready=True,
        )

    service.bind_analysis_runner(analysis_runner)

    first = service.ensure_analysis(session.recording_id)
    second = service.ensure_analysis(session.recording_id)

    assert first.status == "failed"
    assert second.status == "completed"
    assert analysis_calls == 2


def test_replay_case_reuses_exported_test_case_and_writes_manifest(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MUNK_HOME", str(tmp_path))
    backend = FakeBackend()
    service = RecordingService(
        backend_factory=lambda serial: backend,
        capture_interval_seconds=60.0,
    )
    store = RecordingStore()
    session = service.create_session(app_target=build_app_target(), device_ref=None, case_id="case-1")
    service.begin_session(session.recording_id)
    service.record_interaction(
        session.recording_id,
        RecordInteractionCommand(
            client_command_id="cmd-1",
            kind="click",
            forwarding_ack=ForwardingAck(
                kind="pointer",
                payload={"x": 2, "y": 3, "width": 5, "height": 6},
                steps=[
                    ForwardingStep(seq=1, step_kind="pointer_down", payload={"x": 2, "y": 3}),
                    ForwardingStep(seq=2, step_kind="pointer_up", payload={"x": 2, "y": 3}),
                ],
            ),
            payload={"x": 2, "y": 3, "width": 5, "height": 6},
        ),
    )
    service.stop_session(session.recording_id)
    replayed_cases: list[TestCase] = []

    service.bind_analysis_runner(
        lambda bundle, progress_callback=None: RecordingAnalysisResult(  # noqa: ARG005
            recording_id=str(bundle["recording_id"]),
            status="completed",
            test_case=TestCase(
                case_id="case-1",
                title="Generated Case",
                intent="Verify the recorded flow",
                procedure=["Tap generated button"],
                expected=["The visible state changes as expected"],
                runner_goal="Replay the recorded flow and verify the visible state change",
            ),
            export_ready=True,
        )
    )

    def replay_runner(recording_id: str, replay_session, test_case: TestCase) -> RecordingReplayResult:  # noqa: ANN001
        replayed_cases.append(test_case)
        return RecordingReplayResult(
            recording_id=recording_id,
            case_id=test_case.case_id,
            operation_id="op_replay_001",
            run_dir=replay_session.asset_dir / "runs" / "op_replay_001",
            result_path=replay_session.asset_dir / "runs" / "op_replay_001" / "result.json",
            artifact_manifest_path=replay_session.asset_dir / "runs" / "op_replay_001" / "artifact_manifest.json",
            verdict="passed",
        )

    service.bind_replay_runner(replay_runner)

    replay_result = service.replay_case(session.recording_id)
    replay_manifest = store.read_replay_manifest(session.asset_dir)

    assert replay_result.operation_id == "op_replay_001"
    assert replayed_cases
    assert replayed_cases[0].case_id == "case-1"
    assert replayed_cases[0].procedure == ["Tap generated button"]
    assert replay_manifest is not None
    assert replay_manifest.operation_id == "op_replay_001"
