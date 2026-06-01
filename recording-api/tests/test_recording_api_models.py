from __future__ import annotations

from pathlib import Path

from munk.app import AndroidAppIdentity, AppTarget
from munk.recording import (
    LiveViewFrame,
    ObservedTapCommand,
    RecordingAnalysisResult,
    RecordingAnalysisScreenshotRef,
    RecordingAnalysisStep,
    RecordingAnalysisTreeExcerpt,
    RecordingAnalysisTreeFocusHit,
    RecordingAnalysisTreeNode,
    RecordingAssetManifest,
    RecordingSession,
)
from munk.testing import TestCase


def build_app_target() -> AppTarget:
    return AppTarget(
        app_id="app-1",
        platform="android",
        android=AndroidAppIdentity(package_name="com.test.app"),
    )


def test_recording_session_round_trip() -> None:
    session = RecordingSession(
        recording_id="rec-1",
        app_id="app-1",
        app_target=build_app_target(),
        status="created",
        asset_dir=Path("/tmp/assets/app-1/rec-1"),
    )

    dumped = session.model_dump()

    assert dumped["recording_id"] == "rec-1"
    assert dumped["status"] == "created"
    assert dumped["latest_frame_seq"] is None


def test_live_view_frame_round_trip() -> None:
    frame = LiveViewFrame(
        recording_id="rec-1",
        seq=1,
        image_path=Path("/tmp/frame.png"),
        width=1080,
        height=1920,
        entry_identity="com.test.app",
        activity_name=".MainActivity",
    )

    dumped = frame.model_dump()

    assert dumped["seq"] == 1
    assert dumped["entry_identity"] == "com.test.app"
    assert dumped["activity_name"] == ".MainActivity"


def test_recording_asset_manifest_defaults() -> None:
    manifest = RecordingAssetManifest(
        recording_id="rec-1",
        session_path=Path("/tmp/session.json"),
    )

    assert manifest.frame_count == 0
    assert manifest.event_count == 0
    assert manifest.generated_files == {}


def test_observed_tap_command_round_trip() -> None:
    command = ObservedTapCommand(x=10, y=20, width=100, height=200)

    dumped = command.model_dump()

    assert dumped["x"] == 10
    assert dumped["source"] == "scrcpy_bridge"


def test_recording_analysis_result_holds_canonical_test_case() -> None:
    before_ref = RecordingAnalysisScreenshotRef(
        recording_id="rec-1",
        entry_id="entry_000001",
        seq=1,
        role="before",
        observation_id="obs_000001",
        path=Path("/tmp/before.png"),
        compact_tree_excerpt=RecordingAnalysisTreeExcerpt(
            node_count=1,
            focus_hits=[RecordingAnalysisTreeFocusHit(node_id="node_0001", label="Settings", score=2)],
            compact_nodes=[
                RecordingAnalysisTreeNode(
                    node_id="node_0001",
                    class_name="android.widget.TextView",
                    text="Settings",
                )
            ],
        ),
    )
    after_ref = RecordingAnalysisScreenshotRef(
        recording_id="rec-1",
        entry_id="entry_000001",
        seq=1,
        role="after",
        observation_id="obs_000002",
        path=Path("/tmp/after.png"),
    )
    result = RecordingAnalysisResult(
        recording_id="rec-1",
        status="completed",
        test_case=TestCase(
            case_id="case-1",
            title="Open settings",
            intent="Verify settings page can be opened",
            procedure=["Tap settings"],
            expected=["Settings page is visible"],
            runner_goal="Open settings page and verify it is visible",
        ),
        steps=[
            RecordingAnalysisStep(
                recording_id="rec-1",
                entry_id="entry_000001",
                seq=1,
                kind="click",
                action="点击设置",
                intent="打开设置页",
                state_change="设置页显示",
                procedure_step="Tap settings",
                before_observation_id="obs_000001",
                after_observation_id="obs_000002",
                before_screenshot=before_ref,
                after_screenshot=after_ref,
            )
        ],
        export_ready=True,
    )

    dumped = result.model_dump(mode="json")

    assert dumped["test_case"]["case_id"] == "case-1"
    assert dumped["steps"][0]["before_screenshot"]["role"] == "before"
    assert dumped["steps"][0]["before_screenshot"]["compact_tree_excerpt"]["compact_nodes"][0]["text"] == "Settings"
    assert dumped["steps"][0]["intent"] == "打开设置页"
