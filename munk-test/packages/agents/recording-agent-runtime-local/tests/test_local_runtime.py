from __future__ import annotations

import inspect

from munk.app import AndroidAppIdentity, AppTarget
from munk_recording_local.runtime import (
    LocalRecordingRuntime,
    LocalRecordingRuntimeFactory,
    build_recording_runtime_factory,
)


class FakeService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def create_session(self, **kwargs):
        self.calls.append(("create_session", (), kwargs))
        return "created"

    def begin_session(self, recording_id: str):
        self.calls.append(("begin_session", (recording_id,), {}))
        return "begun"

    def get_session(self, recording_id: str):
        self.calls.append(("get_session", (recording_id,), {}))
        return "session"

    def get_live_frame(self, recording_id: str):
        self.calls.append(("get_live_frame", (recording_id,), {}))
        return "frame"

    def stop_session(self, recording_id: str):
        self.calls.append(("stop_session", (recording_id,), {}))
        return "stopped"

    def cancel_session(self, recording_id: str):
        self.calls.append(("cancel_session", (recording_id,), {}))
        return "cancelled"

    def record_tap(self, recording_id: str, command):
        self.calls.append(("record_tap", (recording_id, command), {}))
        return "recorded"

    def list_recorded_events(self, recording_id: str, *, after_seq: int = 0, limit: int = 100):
        self.calls.append(("list_recorded_events", (recording_id,), {"after_seq": after_seq, "limit": limit}))
        return ["event"]

    def diagnose(self):
        self.calls.append(("diagnose", (), {}))
        return "healthy"


def build_app_target() -> AppTarget:
    return AppTarget(
        app_id="app-1",
        platform="android",
        android=AndroidAppIdentity(package_name="com.demo.app"),
    )


def test_runtime_delegates_to_service() -> None:
    service = FakeService()
    runtime = LocalRecordingRuntime(service=service)

    assert runtime.create_session(app_target=build_app_target(), device_ref=None, case_id=None) == "created"
    assert runtime.begin_session("rec-1") == "begun"
    assert runtime.get_session("rec-1") == "session"
    assert runtime.get_live_frame("rec-1") == "frame"
    assert runtime.stop_session("rec-1") == "stopped"
    assert runtime.cancel_session("rec-1") == "cancelled"
    assert runtime.record_tap("rec-1", {"x": 1}) == "recorded"
    assert runtime.list_recorded_events("rec-1", after_seq=2, limit=10) == ["event"]
    assert runtime.diagnose() == "healthy"
    assert [name for name, _, _ in service.calls] == [
        "create_session",
        "begin_session",
        "get_session",
        "get_live_frame",
        "stop_session",
        "cancel_session",
        "record_tap",
        "list_recorded_events",
        "diagnose",
    ]


def test_runtime_exposes_progress_callback_parameter() -> None:
    signature = inspect.signature(LocalRecordingRuntime.analyze_recording)

    assert "progress_callback" in signature.parameters
    assert signature.parameters["progress_callback"].kind is inspect.Parameter.KEYWORD_ONLY


def test_build_recording_runtime_factory_returns_local_factory() -> None:
    factory = build_recording_runtime_factory()

    assert isinstance(factory, LocalRecordingRuntimeFactory)
    assert factory.runtime_id == "local"
