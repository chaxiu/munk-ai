from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from munk.app import AppTarget
from munk.device import DeviceDriver, SupportsAppLifecycle, SupportsDeviceLockState, SupportsDeviceUnlock
from munk.services.errors import StartStateError
from munk.testing import TestCase


class PageNavigator(Protocol):
    def __call__(
        self,
        *,
        device: DeviceDriver,
        app_target: AppTarget,
        page_id: str,
        case: TestCase,
    ) -> None: ...


_PAGE_NAVIGATORS: dict[str, PageNavigator] = {}


def register_page_navigator(app_id: str, navigator: PageNavigator) -> None:
    _PAGE_NAVIGATORS[app_id] = navigator


def prepare_case_start_state(
    *,
    device: DeviceDriver,
    case: TestCase,
    app_target: AppTarget,
    navigator_lookup: Callable[[str], PageNavigator | None] | None = None,
) -> None:
    start_state = case.start_state
    _unlock_device_if_needed(device)

    if start_state.mode == "reset" and isinstance(device, SupportsAppLifecycle) and app_target.entry_identity:
        device.app_stop(app_target.entry_identity)
        device.app_start(app_target.entry_identity)

    page_id = start_state.page_id
    if page_id is None:
        return

    lookup = navigator_lookup or _PAGE_NAVIGATORS.get
    navigator = lookup(app_target.app_id)
    if navigator is None:
        raise StartStateError(
            f"case start_state.page_id '{page_id}' requires a registered page navigator for app '{app_target.app_id}'"
        )

    navigator(
        device=device,
        app_target=app_target,
        page_id=page_id,
        case=case,
    )


def _unlock_device_if_needed(device: DeviceDriver) -> None:
    if not isinstance(device, SupportsDeviceUnlock):
        return
    if isinstance(device, SupportsDeviceLockState):
        locked = device.is_locked()
        if locked is False:
            return
    device.unlock()
