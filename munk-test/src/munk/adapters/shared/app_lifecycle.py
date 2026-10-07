from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from munk.adapters.shared.machine_requests import AppInstallRequest, AppLaunchRequest, AppStopRequest
from munk.device import (
    SupportsAppInstall,
    SupportsAppLifecycle,
    SupportsClose,
    SupportsDeviceLockState,
    SupportsDeviceUnlock,
    resolve_device_runtime_factory,
)
from munk.paths import export_adb_env
from munk.services.machine_contracts import InvalidMachineRequestError


@dataclass(frozen=True)
class AppLifecycleResult:
    action: Literal["launch", "stop", "install"]
    app_id: str
    platform: str
    device_ref: str | None
    entry_identity: str
    artifact_path: str | None = None


class AppLifecycleService:
    def launch(self, request: AppLaunchRequest) -> AppLifecycleResult:
        app_target = request.to_app_target()
        entry_identity = _require_entry_identity(app_target.entry_identity, action="app_launch")
        device = _create_device(app_target=app_target, device_ref=request.device_ref)
        try:
            if not isinstance(device, SupportsAppLifecycle):
                raise InvalidMachineRequestError(f"app_launch is not supported for platform '{app_target.platform}'")
            _unlock_device_if_needed(device)
            device.app_start(entry_identity)
            return AppLifecycleResult(
                action="launch",
                app_id=app_target.app_id,
                platform=app_target.platform,
                device_ref=request.device_ref,
                entry_identity=entry_identity,
            )
        finally:
            _close_device(device)

    def stop(self, request: AppStopRequest) -> AppLifecycleResult:
        app_target = request.to_app_target()
        entry_identity = _require_entry_identity(app_target.entry_identity, action="app_stop")
        device = _create_device(app_target=app_target, device_ref=request.device_ref)
        try:
            if not isinstance(device, SupportsAppLifecycle):
                raise InvalidMachineRequestError(f"app_stop is not supported for platform '{app_target.platform}'")
            device.app_stop(entry_identity)
            return AppLifecycleResult(
                action="stop",
                app_id=app_target.app_id,
                platform=app_target.platform,
                device_ref=request.device_ref,
                entry_identity=entry_identity,
            )
        finally:
            _close_device(device)

    def install(self, request: AppInstallRequest) -> AppLifecycleResult:
        app_target = request.to_app_target()
        entry_identity = _require_entry_identity(app_target.entry_identity, action="app_install")
        artifact_path = request.artifact_path
        if app_target.platform != "android":
            raise InvalidMachineRequestError(f"app_install is not supported for platform '{app_target.platform}'")
        if artifact_path.suffix.lower() != ".apk":
            raise InvalidMachineRequestError("android app_install currently requires an .apk artifact_path")
        if not artifact_path.exists():
            raise InvalidMachineRequestError(f"artifact_path not found: {artifact_path}")
        device = _create_device(app_target=app_target, device_ref=request.device_ref)
        try:
            if not isinstance(device, SupportsAppInstall):
                raise InvalidMachineRequestError(f"app_install is not supported for platform '{app_target.platform}'")
            device.app_install(str(artifact_path))
            return AppLifecycleResult(
                action="install",
                app_id=app_target.app_id,
                platform=app_target.platform,
                device_ref=request.device_ref,
                entry_identity=entry_identity,
                artifact_path=str(artifact_path),
            )
        finally:
            _close_device(device)


def _create_device(*, app_target, device_ref: str | None):  # noqa: ANN001
    export_adb_env()
    factory = resolve_device_runtime_factory(platform=app_target.platform)
    return factory.create_device(device_ref=device_ref, app_target=app_target)


def _close_device(device: object) -> None:
    if isinstance(device, SupportsClose):
        device.close()


def _unlock_device_if_needed(device: object) -> None:
    if not isinstance(device, SupportsDeviceUnlock):
        return
    if isinstance(device, SupportsDeviceLockState):
        locked = device.is_locked()
        if locked is False:
            return
    device.unlock()


def _require_entry_identity(entry_identity: str | None, *, action: str) -> str:
    if not entry_identity:
        raise InvalidMachineRequestError(f"{action} requires an app_target with entry_identity")
    return entry_identity
