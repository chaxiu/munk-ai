from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from munk.app import AndroidAppIdentity, AppTarget
from munk.recording import (
    LiveViewFrame,
    RecordedInputEvent,
    RecordingAnalysisResult,
    RecordingAnalysisScreenshotRef,
    RecordingAnalysisStep,
)
from munk.testing import TestCase
from munk_recording_local.store import RecordingStore


def build_app_target(app_id: str = "demo-app", package_name: str = "com.demo.app") -> AppTarget:
    return AppTarget(
        app_id=app_id,
        platform="android",
        android=AndroidAppIdentity(package_name=package_name),
    )


def test_create_session_initializes_recording_layout(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MUNK_HOME", str(tmp_path))
    store = RecordingStore()

    session = store.create_session(
        app_target=build_app_target(),
        device_ref="SER123",
        case_id="case-1",
    )

    assert session.status == "created"
    assert (session.asset_dir / "live").is_dir()
    assert (session.asset_dir / "frames").is_dir()
    assert store.session_path(session.asset_dir).is_file()
    assert store.manifest_path(session.asset_dir).is_file()


def test_write_frame_updates_manifest_and_current_files(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MUNK_HOME", str(tmp_path))
    store = RecordingStore()
    session = store.create_session(
        app_target=build_app_target(),
        device_ref=None,
        case_id=None,
    )
    frame = LiveViewFrame(
        recording_id=session.recording_id,
        seq=1,
        image_path=store.frame_image_path(session.asset_dir, 1),
        width=4,
        height=3,
        entry_identity="com.demo.app",
        activity_name=".MainActivity",
    )

    manifest = store.write_frame(session, frame, np.zeros((3, 4, 3), dtype=np.uint8))

    assert manifest.frame_count == 1
    assert manifest.latest_frame_seq == 1
    assert store.current_image_path(session.asset_dir).is_file()
    assert store.current_meta_path(session.asset_dir).is_file()
    assert store.frame_image_path(session.asset_dir, 1).is_file()
    assert store.frame_meta_path(session.asset_dir, 1).is_file()

    current_meta = json.loads(store.current_meta_path(session.asset_dir).read_text(encoding="utf-8"))
    assert current_meta["seq"] == 1
    assert current_meta["entry_identity"] == "com.demo.app"


def test_append_event_updates_manifest(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MUNK_HOME", str(tmp_path))
    store = RecordingStore()
    session = store.create_session(
        app_target=build_app_target(),
        device_ref=None,
        case_id=None,
    )
    event = RecordedInputEvent(
        event_id="tap_000001",
        recording_id=session.recording_id,
        kind="click",
        payload={"x": 1, "y": 2},
    )

    manifest = store.append_event(session, event)

    assert manifest.event_count == 1
    assert store.events_path(session.asset_dir).is_file()
    events = store.read_events(session.asset_dir)
    assert len(events) == 1
    assert events[0].event_id == "tap_000001"


def test_store_writes_analysis_and_export_files(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MUNK_HOME", str(tmp_path))
    store = RecordingStore()
    session = store.create_session(
        app_target=build_app_target(),
        device_ref=None,
        case_id="case-1",
    )
    analysis = RecordingAnalysisResult(
        recording_id=session.recording_id,
        status="completed",
        test_case=TestCase(
            case_id="case-1",
            title="Generated Case",
            intent="Verify the recorded flow",
            procedure=["Tap generated button"],
            expected=["The visible state changes as expected"],
            runner_goal="Replay the recorded flow and verify the visible state change",
        ),
        steps=[
            RecordingAnalysisStep(
                recording_id=session.recording_id,
                entry_id="entry_000001",
                seq=1,
                kind="click",
                action="点击生成按钮",
                intent="打开成功页",
                state_change="成功提示显示",
                procedure_step="为打开成功页，点击生成按钮，成功提示显示",
                before_observation_id="obs_000001",
                after_observation_id="obs_000002",
                before_screenshot=RecordingAnalysisScreenshotRef(
                    recording_id=session.recording_id,
                    entry_id="entry_000001",
                    seq=1,
                    role="before",
                    observation_id="obs_000001",
                    path=session.asset_dir / "frames" / "before.png",
                ),
                after_screenshot=RecordingAnalysisScreenshotRef(
                    recording_id=session.recording_id,
                    entry_id="entry_000001",
                    seq=1,
                    role="after",
                    observation_id="obs_000002",
                    path=session.asset_dir / "frames" / "after.png",
                ),
            )
        ],
        export_ready=True,
    )

    store.write_analysis_result(session.asset_dir, analysis)
    assert analysis.test_case is not None
    store.write_test_case(session.asset_dir, analysis.test_case.model_dump(mode="json"))

    assert store.analysis_path(session.asset_dir).is_file()
    assert store.test_case_path(session.asset_dir).is_file()
    analysis_payload = json.loads(store.analysis_path(session.asset_dir).read_text(encoding="utf-8"))
    persisted = json.loads(store.test_case_path(session.asset_dir).read_text(encoding="utf-8"))
    assert analysis_payload["steps"][0]["intent"] == "打开成功页"
    assert analysis_payload["steps"][0]["state_change"] == "成功提示显示"
    assert analysis_payload["steps"][0]["procedure_step"] == "为打开成功页，点击生成按钮，成功提示显示"
    assert persisted["case_id"] == "case-1"
    assert persisted["procedure"] == ["Tap generated button"]
