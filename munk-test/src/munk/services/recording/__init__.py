from __future__ import annotations

from importlib import import_module

__all__ = [
    "DEFAULT_RECORDING_BRIDGE_FALLBACK_RETRIES",
    "DEFAULT_RECORDING_BRIDGE_HOST",
    "DEFAULT_RECORDING_BRIDGE_PORT",
    "DEFAULT_RECORDING_BRIDGE_STARTUP_TIMEOUT_SECONDS",
    "RecordingBridgeError",
    "RecordingBridgeManager",
    "RecordingBridgeSession",
    "RecordingBridgeStartupAttempt",
    "RecordingReplayService",
    "RecordingSessionService",
    "resolve_recording_runtime",
]

_EXPORTS = {
    "DEFAULT_RECORDING_BRIDGE_FALLBACK_RETRIES": (
        ".bridge_manager",
        "DEFAULT_RECORDING_BRIDGE_FALLBACK_RETRIES",
    ),
    "DEFAULT_RECORDING_BRIDGE_HOST": (".bridge_manager", "DEFAULT_RECORDING_BRIDGE_HOST"),
    "DEFAULT_RECORDING_BRIDGE_PORT": (".bridge_manager", "DEFAULT_RECORDING_BRIDGE_PORT"),
    "DEFAULT_RECORDING_BRIDGE_STARTUP_TIMEOUT_SECONDS": (
        ".bridge_manager",
        "DEFAULT_RECORDING_BRIDGE_STARTUP_TIMEOUT_SECONDS",
    ),
    "RecordingBridgeError": (".bridge_manager", "RecordingBridgeError"),
    "RecordingBridgeManager": (".bridge_manager", "RecordingBridgeManager"),
    "RecordingBridgeSession": (".bridge_manager", "RecordingBridgeSession"),
    "RecordingBridgeStartupAttempt": (".bridge_manager", "RecordingBridgeStartupAttempt"),
    "RecordingReplayService": (".replay_service", "RecordingReplayService"),
    "RecordingSessionService": (".session_service", "RecordingSessionService"),
    "resolve_recording_runtime": (".runtime", "resolve_recording_runtime"),
}


def __getattr__(name: str):
    try:
        module_name, attr_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    module = import_module(module_name, __name__)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
