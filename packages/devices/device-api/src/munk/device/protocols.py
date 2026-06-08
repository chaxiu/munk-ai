from __future__ import annotations

from typing import Protocol, runtime_checkable

from munk.perception import ObservationTree
from munk.perception.image import BgrImage

from .models import CurrentAppState, RuntimeLogEntry


@runtime_checkable
class DeviceDriver(Protocol):
    """Cross-platform minimal interaction contract for mobile and future Web runtimes."""

    def screenshot_bgr(self) -> BgrImage: ...

    def click(self, x: int, y: int) -> None: ...

    def long_press(self, x: int, y: int, duration: float | None = None) -> None: ...

    def scroll(
        self,
        start: tuple[int, int],
        end: tuple[int, int],
        duration: float | None = None,
    ) -> None: ...

    def press(self, key: str) -> None: ...

    def input_text(self, text: str) -> None: ...

    def app_current(self) -> CurrentAppState: ...

    def window_size(self) -> tuple[int, int]: ...

    def capture_observation_tree(self) -> ObservationTree | None: ...


@runtime_checkable
class SupportsTextClear(Protocol):
    """Optional capability for focused text controls that support explicit clear."""

    def clear_text(self) -> None: ...


@runtime_checkable
class SupportsSoftKeyboardDismiss(Protocol):
    """Optional soft-keyboard capability used only when the runtime exposes it."""

    def dismiss_soft_keyboard(self) -> None: ...


@runtime_checkable
class SupportsSoftKeyboardVisibility(Protocol):
    """Optional soft-keyboard visibility probe."""

    def is_soft_keyboard_visible(self) -> bool | None: ...


@runtime_checkable
class SupportsSoftKeyboardBounds(Protocol):
    """Optional soft-keyboard bounds probe."""

    def get_soft_keyboard_bounds(self) -> tuple[int, int, int, int] | None: ...


@runtime_checkable
class SupportsAppLifecycle(Protocol):
    """Optional entry-target reset capability used by start-state preparation."""

    def app_start(self, entry_identity: str) -> None: ...

    def app_stop(self, entry_identity: str) -> None: ...


@runtime_checkable
class SupportsAppInstall(Protocol):
    """Optional application install capability for runtimes that can install artifacts."""

    def app_install(self, artifact_path: str) -> None: ...


@runtime_checkable
class SupportsDeviceUnlock(Protocol):
    """Optional device unlock capability used by pre-run preparation."""

    def unlock(self) -> None: ...


@runtime_checkable
class SupportsDeviceLockState(Protocol):
    """Optional device lock-state probe used for diagnostics and idempotent unlocks."""

    def is_locked(self) -> bool | None: ...


@runtime_checkable
class SupportsThreadBoundDeviceCalls(Protocol):
    """Optional capability for runtimes whose device calls must stay on the owning thread."""

    @property
    def device_calls_thread_safe(self) -> bool: ...


@runtime_checkable
class SupportsRuntimeLogs(Protocol):
    """Optional runtime log stream capability for diagnostics and judge evidence."""

    def start_log_session(self) -> None: ...

    def drain_runtime_logs(self) -> list[RuntimeLogEntry]: ...

    def stop_log_session(self) -> None: ...


@runtime_checkable
class SupportsClose(Protocol):
    """Optional resource cleanup contract for runtimes with explicit teardown."""

    def close(self) -> None: ...
