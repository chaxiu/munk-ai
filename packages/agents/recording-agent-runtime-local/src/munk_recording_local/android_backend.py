from __future__ import annotations

from munk.app import AndroidAppIdentity, AppTarget
from munk_device_android import AndroidDevice


class AndroidRecordingBackend(AndroidDevice):
    @classmethod
    def connect(cls, device_ref: str | None = None) -> "AndroidRecordingBackend":
        app_target = AppTarget(
            app_id="recording-android",
            platform="android",
            android=AndroidAppIdentity(package_name="unknown"),
        )
        device = AndroidDevice.connect(device_ref, app_target=app_target)
        return cls(device._device, app_target=app_target)
