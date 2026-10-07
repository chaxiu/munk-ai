from __future__ import annotations

from threading import Lock

from munk.recording import RecordingRuntime, RecordingRuntimeHealth
from munk.recording.errors import RecordingRuntimeUnavailableError
from munk.recording.runtime import create_recording_runtime, diagnose_recording_runtime

_RUNTIME_CACHE: dict[str | None, RecordingRuntime] = {}
_RUNTIME_CACHE_LOCK = Lock()


def resolve_recording_runtime(*, runtime_name: str | None = None) -> RecordingRuntime:
    try:
        with _RUNTIME_CACHE_LOCK:
            runtime = _RUNTIME_CACHE.get(runtime_name)
            if runtime is None:
                runtime = create_recording_runtime(runtime_name=runtime_name)
                _RUNTIME_CACHE[runtime_name] = runtime
            return runtime
    except LookupError as exc:
        raise RecordingRuntimeUnavailableError(str(exc)) from exc


def recording_runtime_health(*, runtime_name: str | None = None) -> RecordingRuntimeHealth:
    return diagnose_recording_runtime(runtime_name=runtime_name)


def clear_recording_runtime_cache() -> None:
    with _RUNTIME_CACHE_LOCK:
        _RUNTIME_CACHE.clear()
