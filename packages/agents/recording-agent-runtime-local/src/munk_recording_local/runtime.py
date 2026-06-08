from __future__ import annotations

from typing import Any, Callable

from munk.app import AppTarget
from munk.recording import RecordingAnalysisResult, RecordingReplayResult, RecordingRuntimeHealth, RecordingSession
from munk.testing import TestCase

from .service import RecordingService


class LocalRecordingRuntime:
    def __init__(self, *, service: RecordingService | None = None) -> None:
        self._service = service or RecordingService()

    def create_session(
        self,
        *,
        app_target: AppTarget,
        device_ref: str | None = None,
        case_id: str | None = None,
    ):
        return self._service.create_session(
            app_target=app_target,
            device_ref=device_ref,
            case_id=case_id,
        )

    def begin_session(self, recording_id: str):
        return self._service.begin_session(recording_id)

    def get_session(self, recording_id: str):
        return self._service.get_session(recording_id)

    def get_live_frame(self, recording_id: str):
        return self._service.get_live_frame(recording_id)

    def stop_session(self, recording_id: str):
        return self._service.stop_session(recording_id)

    def cancel_session(self, recording_id: str):
        return self._service.cancel_session(recording_id)

    def record_tap(self, recording_id: str, command):
        return self._service.record_tap(recording_id, command)

    def record_interaction(self, recording_id: str, command):
        return self._service.record_interaction(recording_id, command)

    def list_recorded_events(
        self,
        recording_id: str,
        *,
        after_seq: int = 0,
        limit: int = 100,
    ):
        return self._service.list_recorded_events(recording_id, after_seq=after_seq, limit=limit)

    def list_timeline(
        self,
        recording_id: str,
        *,
        after_seq: int = 0,
        limit: int = 100,
    ):
        return self._service.list_timeline(recording_id, after_seq=after_seq, limit=limit)

    def get_observation(self, recording_id: str, observation_id: str):
        return self._service.get_observation(recording_id, observation_id)

    def bind_analysis_runner(
        self,
        analysis_runner: Callable[[dict[str, Any], Callable[[str, dict[str, Any]], None] | None], RecordingAnalysisResult],
    ) -> None:
        self._service.bind_analysis_runner(analysis_runner)

    def bind_replay_runner(
        self,
        replay_runner: Callable[[str, RecordingSession, TestCase], RecordingReplayResult],
    ) -> None:
        self._service.bind_replay_runner(replay_runner)

    def load_recording_assets(self, recording_id: str):
        return self._service.load_recording_assets(recording_id)

    def load_analysis_result(self, recording_id: str):
        return self._service.load_analysis_result(recording_id)

    def load_exported_test_case(self, recording_id: str):
        return self._service.load_exported_test_case(recording_id)

    def load_export_manifest(self, recording_id: str):
        return self._service.load_export_manifest(recording_id)

    def analyze_recording(
        self,
        recording_id: str,
        *,
        progress_callback: Callable[[str, dict[str, Any]], None] | None = None,
    ):
        return self._service.analyze_recording(recording_id, progress_callback=progress_callback)

    def export_case(self, recording_id: str):
        return self._service.export_case(recording_id)

    def replay_case(self, recording_id: str):
        return self._service.replay_case(recording_id)

    def diagnose(self) -> RecordingRuntimeHealth:
        return self._service.diagnose()


class LocalRecordingRuntimeFactory:
    runtime_id = "local"

    def create_runtime(self) -> LocalRecordingRuntime:
        return LocalRecordingRuntime()

    def diagnose(self) -> RecordingRuntimeHealth:
        return RecordingService().diagnose()


def build_recording_runtime_factory() -> LocalRecordingRuntimeFactory:
    return LocalRecordingRuntimeFactory()
