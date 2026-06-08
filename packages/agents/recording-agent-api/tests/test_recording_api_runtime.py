from __future__ import annotations

import inspect

from munk.recording.errors import RecordingRuntimeConflictError, RecordingRuntimeUnavailableError
from munk.recording.health import RecordingRuntimeHealth
from munk.recording.runtime import RecordingRuntime, diagnose_recording_runtime, resolve_recording_runtime_factory


def test_resolve_runtime_raises_when_no_runtime_installed(monkeypatch) -> None:
    monkeypatch.setattr(
        "munk.recording.runtime.list_recording_runtime_factories",
        lambda: {},
    )

    try:
        resolve_recording_runtime_factory()
    except RecordingRuntimeUnavailableError as exc:
        assert "no recording runtime installed" in str(exc)
    else:
        raise AssertionError("expected RecordingRuntimeUnavailableError")


def test_resolve_runtime_raises_when_multiple_runtimes_are_installed(monkeypatch) -> None:
    monkeypatch.setattr(
        "munk.recording.runtime.list_recording_runtime_factories",
        lambda: {"local": object(), "remote": object()},
    )

    try:
        resolve_recording_runtime_factory()
    except RecordingRuntimeConflictError as exc:
        assert "multiple recording runtimes installed" in str(exc)
    else:
        raise AssertionError("expected RecordingRuntimeConflictError")


def test_resolve_runtime_returns_named_runtime(monkeypatch) -> None:
    factory = object()
    monkeypatch.setattr(
        "munk.recording.runtime.list_recording_runtime_factories",
        lambda: {"local": factory},
    )

    resolved = resolve_recording_runtime_factory("local")

    assert resolved is factory


def test_diagnose_runtime_forwards_to_factory(monkeypatch) -> None:
    class FakeFactory:
        runtime_id = "local"

        def diagnose(self) -> RecordingRuntimeHealth:
            return RecordingRuntimeHealth(runtime_id="local", status="ok", message="healthy")

    monkeypatch.setattr(
        "munk.recording.runtime.resolve_recording_runtime_factory",
        lambda runtime_name=None: FakeFactory(),
    )

    health = diagnose_recording_runtime()

    assert health.runtime_id == "local"
    assert health.status == "ok"


def test_recording_runtime_protocol_exposes_progress_callback() -> None:
    signature = inspect.signature(RecordingRuntime.analyze_recording)

    assert "progress_callback" in signature.parameters
    assert signature.parameters["progress_callback"].kind is inspect.Parameter.KEYWORD_ONLY
