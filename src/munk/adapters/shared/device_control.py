from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from munk.app import AndroidAppIdentity, AppTarget
from munk.device import (
    DeviceDescriptor,
    SupportsClose,
    SupportsDeviceLockState,
    SupportsDeviceScreenState,
    SupportsDeviceUnlock,
    resolve_device_runtime_factory,
)
from munk.paths import export_adb_env
from munk.services.machine_contracts import InvalidMachineRequestError

from .device_queries import coerce_platform, list_discovered_devices
from .payload_models import DeviceStateData

UnlockStrategy = Literal["swipe"]


@dataclass(frozen=True)
class DeviceUnlockResult:
    platform: str
    device_ref: str
    strategy: UnlockStrategy
    success: bool
    changed: bool
    message: str
    before: DeviceStateData
    after: DeviceStateData


class DeviceControlService:
    def get_state(self, *, device_ref: str, platform: str | None = None) -> DeviceStateData:
        descriptor = _resolve_descriptor(device_ref=device_ref, platform=platform)
        state = DeviceStateData(
            platform=descriptor.platform,
            device_ref=descriptor.device_ref,
            display_name=descriptor.display_name,
            kind=descriptor.kind,
            availability=descriptor.availability,
            is_booted=descriptor.is_booted,
            automation_ready=_base_automation_ready(descriptor),
            unlock_strategies=["swipe"] if descriptor.platform == "android" else [],
            blockers=_base_blockers(descriptor),
            raw=dict(descriptor.raw),
        )
        if descriptor.platform != "android":
            return state
        try:
            device = _create_management_device(descriptor)
        except Exception:
            state.automation_ready = False
            if "automation_probe_failed" not in state.blockers:
                state.blockers.append("automation_probe_failed")
            return state
        try:
            if isinstance(device, SupportsDeviceLockState):
                state.is_locked = device.is_locked()
            if isinstance(device, SupportsDeviceScreenState):
                state.is_screen_on = device.is_screen_on()
        finally:
            _close_device(device)
        if state.is_locked is True and "device_locked" not in state.blockers:
            state.blockers.append("device_locked")
        if state.is_screen_on is False and "screen_off" not in state.blockers:
            state.blockers.append("screen_off")
        if state.is_locked is True or state.is_screen_on is False:
            state.automation_ready = False
        return state

    def unlock(
        self,
        *,
        device_ref: str,
        platform: str | None = None,
        strategy: UnlockStrategy = "swipe",
    ) -> DeviceUnlockResult:
        descriptor = _resolve_descriptor(device_ref=device_ref, platform=platform)
        if descriptor.platform != "android":
            raise InvalidMachineRequestError(
                f"device_unlock with strategy '{strategy}' is not supported for platform '{descriptor.platform}'"
            )
        before = self.get_state(device_ref=device_ref, platform=descriptor.platform)
        device = _create_management_device(descriptor)
        try:
            if not isinstance(device, SupportsDeviceUnlock):
                raise InvalidMachineRequestError(
                    f"device_unlock is not supported for platform '{descriptor.platform}'"
                )
            device.unlock()
        finally:
            _close_device(device)
        after = self.get_state(device_ref=device_ref, platform=descriptor.platform)
        success = after.is_locked is False
        changed = before.is_locked != after.is_locked or before.is_screen_on != after.is_screen_on
        message = "device unlocked via swipe" if success else "device unlock attempted but still appears locked"
        return DeviceUnlockResult(
            platform=descriptor.platform,
            device_ref=descriptor.device_ref,
            strategy=strategy,
            success=success,
            changed=changed,
            message=message,
            before=before,
            after=after,
        )


def _resolve_descriptor(*, device_ref: str, platform: str | None) -> DeviceDescriptor:
    items = list_discovered_devices(platform)
    matches = [item for item in items if item.device_ref == device_ref]
    if not matches:
        if platform is None:
            raise InvalidMachineRequestError(f"device_ref '{device_ref}' was not found")
        raise InvalidMachineRequestError(f"device_ref '{device_ref}' was not found for platform '{platform}'")
    if len(matches) > 1:
        raise InvalidMachineRequestError(
            f"device_ref '{device_ref}' is ambiguous across platforms; pass --platform explicitly"
        )
    return matches[0]


def _create_management_device(descriptor: DeviceDescriptor) -> object:
    export_adb_env()
    factory = resolve_device_runtime_factory(platform=coerce_platform(descriptor.platform))
    return factory.create_device(
        device_ref=descriptor.device_ref,
        app_target=_build_management_app_target(descriptor.platform),
    )


def _build_management_app_target(platform: str) -> AppTarget:
    if platform == "android":
        return AppTarget(
            app_id="_device_control",
            platform="android",
            android=AndroidAppIdentity(package_name="sh.munk.device.control"),
        )
    raise InvalidMachineRequestError(f"device control is not supported for platform '{platform}'")


def _close_device(device: object) -> None:
    if isinstance(device, SupportsClose):
        device.close()


def _base_automation_ready(descriptor: DeviceDescriptor) -> bool:
    if descriptor.availability != "available":
        return False
    if descriptor.is_booted is False:
        return False
    if descriptor.platform == "ios" and descriptor.kind == "real_device":
        bridge_visible = bool(descriptor.raw.get("bridge_visible"))
        appium_visible = bool(descriptor.raw.get("appium_visible"))
        return bridge_visible or appium_visible
    return True


def _base_blockers(descriptor: DeviceDescriptor) -> list[str]:
    blockers: list[str] = []
    if descriptor.availability != "available":
        blockers.append("device_unavailable")
    if descriptor.is_booted is False:
        blockers.append("device_not_booted")
    if descriptor.platform == "ios" and descriptor.kind == "real_device":
        if not bool(descriptor.raw.get("bridge_visible") or descriptor.raw.get("appium_visible")):
            blockers.append("automation_bridge_unavailable")
    return blockers
