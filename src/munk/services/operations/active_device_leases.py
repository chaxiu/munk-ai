from __future__ import annotations

from collections.abc import Callable, Iterable
from threading import Lock
from typing import Any

from munk.device import SupportsClose


class DeviceLeaseRevokedError(RuntimeError):
    """Raised when a runner tries to use a device after cancel revoked its lease."""


class RevocableDevice:
    """Process-local device handle that cancel can invalidate without killing the runner.

    Optional DeviceDriver capabilities are installed as instance attributes so
    ``isinstance(..., Supports*)`` runtime_checkable protocols keep working.
    """

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self._revoked = False
        self._lock = Lock()
        self._install_capability_forwards(inner)

    def _install_capability_forwards(self, inner: Any) -> None:
        # Class already defines the core DeviceDriver surface + close/revoke.
        owned = {name for name in dir(RevocableDevice) if not name.startswith("_")}
        for name in dir(inner):
            if name.startswith("_") or name in owned:
                continue
            try:
                value = getattr(inner, name)
            except Exception:  # noqa: BLE001
                continue
            if callable(value):
                setattr(self, name, self._guarded_callable(value))
            else:
                setattr(self, name, value)

    def _guarded_callable(self, fn: Callable[..., Any]) -> Callable[..., Any]:
        def guarded(*args: Any, **kwargs: Any) -> Any:
            self._ensure_active()
            return fn(*args, **kwargs)

        return guarded

    @property
    def revoked(self) -> bool:
        with self._lock:
            return self._revoked

    @property
    def inner(self) -> Any:
        return self._inner

    def revoke(self) -> None:
        with self._lock:
            if self._revoked:
                return
            self._revoked = True
            inner = self._inner
        self._close_inner(inner)

    def close(self) -> None:
        self.revoke()

    def _ensure_active(self) -> Any:
        with self._lock:
            if self._revoked:
                raise DeviceLeaseRevokedError("device lease revoked after cancel")
            return self._inner

    @staticmethod
    def _close_inner(inner: Any) -> None:
        close = getattr(inner, "close", None)
        if not callable(close) and not isinstance(inner, SupportsClose):
            return
        if not callable(close):
            return
        try:
            close()
        except Exception:  # noqa: BLE001
            return

    def screenshot_bgr(self) -> Any:
        return self._ensure_active().screenshot_bgr()

    def click(self, x: int, y: int) -> None:
        self._ensure_active().click(x, y)

    def long_press(self, x: int, y: int, duration: float | None = None) -> None:
        self._ensure_active().long_press(x, y, duration=duration)

    def scroll(
        self,
        start: tuple[int, int],
        end: tuple[int, int],
        duration: float | None = None,
    ) -> None:
        self._ensure_active().scroll(start, end, duration=duration)

    def drag(
        self,
        start: tuple[int, int],
        end: tuple[int, int],
        duration: float | None = None,
    ) -> None:
        self._ensure_active().drag(start, end, duration=duration)

    def press(self, key: str) -> None:
        self._ensure_active().press(key)

    def input_text(self, text: str) -> None:
        self._ensure_active().input_text(text)

    def app_current(self) -> Any:
        return self._ensure_active().app_current()

    def window_size(self) -> tuple[int, int]:
        return self._ensure_active().window_size()

    def capture_observation_tree(self) -> Any:
        return self._ensure_active().capture_observation_tree()


class ActiveDeviceLeaseRegistry:
    """Maps live operation_id -> revocable device for in-process cancel."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._leases: dict[str, RevocableDevice] = {}

    def bind(self, operation_id: str, device: RevocableDevice) -> None:
        with self._lock:
            previous = self._leases.get(operation_id)
            self._leases[operation_id] = device
        if previous is not None and previous is not device:
            previous.revoke()

    def unbind(self, operation_id: str, device: object | None = None) -> None:
        with self._lock:
            current = self._leases.get(operation_id)
            if current is None:
                return
            if device is not None and current is not device:
                return
            self._leases.pop(operation_id, None)

    def revoke(self, operation_id: str) -> bool:
        with self._lock:
            device = self._leases.pop(operation_id, None)
        if device is None:
            return False
        device.revoke()
        return True

    def revoke_tree(self, operation_ids: Iterable[str]) -> list[str]:
        revoked: list[str] = []
        for operation_id in operation_ids:
            if self.revoke(operation_id):
                revoked.append(operation_id)
        return revoked

    def clear(self) -> None:
        with self._lock:
            devices = list(self._leases.values())
            self._leases.clear()
        for device in devices:
            device.revoke()


_REGISTRY = ActiveDeviceLeaseRegistry()


def get_active_device_lease_registry() -> ActiveDeviceLeaseRegistry:
    return _REGISTRY


def reset_active_device_lease_registry() -> None:
    """Test helper: drop all leases without revoking (avoids closing shared fakes)."""
    with _REGISTRY._lock:
        _REGISTRY._leases.clear()


def bind_operation_device(*, operation_id: str | None, device: Any) -> Any:
    if operation_id is None:
        return device
    if isinstance(device, RevocableDevice):
        revocable = device
    else:
        revocable = RevocableDevice(device)
    get_active_device_lease_registry().bind(operation_id, revocable)
    return revocable


def unbind_operation_device(*, operation_id: str | None, device: Any = None) -> None:
    if operation_id is None:
        return
    get_active_device_lease_registry().unbind(operation_id, device)
