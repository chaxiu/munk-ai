from __future__ import annotations

from importlib.metadata import entry_points
from typing import Callable, Protocol

from munk.app import AppTarget

from .errors import RecordingRuntimeConflictError, RecordingRuntimeUnavailableError
from .health import RecordingRuntimeHealth
from .models import (
    LiveViewFrame,
    ObservationSnapshot,
    ObservedTapCommand,
    RecordedInputEvent,
    RecordingAnalysisResult,
    RecordingCaseExport,
    RecordingReplayResult,
    RecordingSession,
    RecordInteractionCommand,
    TimelineEntry,
)

ENTRY_POINT_GROUP = "munk.recording.runtimes"


class RecordingRuntime(Protocol):
    def create_session(
        self,
        *,
        app_target: AppTarget,
        device_ref: str | None = None,
        case_id: str | None = None,
    ) -> RecordingSession: ...

    def begin_session(self, recording_id: str) -> RecordingSession: ...

    def get_session(self, recording_id: str) -> RecordingSession: ...

    def get_live_frame(self, recording_id: str) -> LiveViewFrame | None: ...

    def stop_session(self, recording_id: str) -> RecordingSession: ...

    def cancel_session(self, recording_id: str) -> RecordingSession: ...

    def record_tap(self, recording_id: str, command: ObservedTapCommand) -> RecordedInputEvent: ...

    def record_interaction(self, recording_id: str, command: RecordInteractionCommand) -> TimelineEntry: ...

    def list_recorded_events(
        self,
        recording_id: str,
        *,
        after_seq: int = 0,
        limit: int = 100,
    ) -> list[RecordedInputEvent]: ...

    def list_timeline(
        self,
        recording_id: str,
        *,
        after_seq: int = 0,
        limit: int = 100,
    ) -> list[TimelineEntry]: ...

    def get_observation(self, recording_id: str, observation_id: str) -> ObservationSnapshot: ...

    def analyze_recording(
        self,
        recording_id: str,
        *,
        progress_callback: Callable[[str, dict[str, object]], None] | None = None,
    ) -> RecordingAnalysisResult: ...

    def export_case(self, recording_id: str) -> RecordingCaseExport: ...

    def replay_case(self, recording_id: str) -> RecordingReplayResult: ...

    def diagnose(self) -> RecordingRuntimeHealth: ...


class RecordingRuntimeFactory(Protocol):
    runtime_id: str

    def create_runtime(self) -> RecordingRuntime: ...

    def diagnose(self) -> RecordingRuntimeHealth: ...


def list_recording_runtime_factories() -> dict[str, RecordingRuntimeFactory]:
    factories: dict[str, RecordingRuntimeFactory] = {}
    for entry_point in entry_points(group=ENTRY_POINT_GROUP):
        factory = entry_point.load()()
        factories[entry_point.name] = factory
    return factories


def resolve_recording_runtime_factory(runtime_name: str | None = None) -> RecordingRuntimeFactory:
    factories = list_recording_runtime_factories()
    if runtime_name:
        factory = factories.get(runtime_name)
        if factory is None:
            available = ", ".join(sorted(factories)) or "none"
            raise RecordingRuntimeUnavailableError(
                f"recording runtime '{runtime_name}' not found; available runtimes: {available}"
            )
        return factory
    if not factories:
        raise RecordingRuntimeUnavailableError(
            "no recording runtime installed; install the recording local runtime package first"
        )
    if len(factories) > 1:
        available = ", ".join(sorted(factories))
        raise RecordingRuntimeConflictError(
            "multiple recording runtimes installed; explicit runtime selection is required: "
            f"{available}"
        )
    return next(iter(factories.values()))


def create_recording_runtime(*, runtime_name: str | None = None) -> RecordingRuntime:
    factory = resolve_recording_runtime_factory(runtime_name)
    return factory.create_runtime()


def diagnose_recording_runtime(*, runtime_name: str | None = None) -> RecordingRuntimeHealth:
    factory = resolve_recording_runtime_factory(runtime_name)
    return factory.diagnose()
