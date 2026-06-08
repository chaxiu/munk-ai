from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

AppPlatform = Literal["android", "ios", "web"]


def empty_launch_context() -> dict[str, str]:
    return {}


class AndroidAppIdentity(BaseModel):
    package_name: str
    activity_name: str | None = None


class IOSAppIdentity(BaseModel):
    bundle_id: str


class WebAppIdentity(BaseModel):
    base_url: str | None = None
    origin: str | None = None


class AppTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app_id: str
    platform: AppPlatform
    entry_identity: str | None = None
    launch_context: dict[str, str] = Field(default_factory=empty_launch_context)
    android: AndroidAppIdentity | None = None
    ios: IOSAppIdentity | None = None
    web: WebAppIdentity | None = None

    @model_validator(mode="after")
    def validate_platform_identity(self) -> "AppTarget":
        platform_fields = {
            "android": self.android,
            "ios": self.ios,
            "web": self.web,
        }
        active_fields = [name for name, value in platform_fields.items() if value is not None]
        expected_field = self.platform
        if active_fields != [expected_field]:
            raise ValueError(
                f"app_target for platform '{self.platform}' must define only '{expected_field}' identity details"
            )
        derived_entry_identity = self._derive_entry_identity()
        if self.entry_identity is None:
            object.__setattr__(self, "entry_identity", derived_entry_identity)
        elif self.entry_identity != derived_entry_identity:
            raise ValueError(
                f"app_target entry_identity must match the identity implied by platform '{self.platform}'"
            )
        return self

    def _derive_entry_identity(self) -> str | None:
        if self.platform == "android" and self.android is not None:
            return self.android.package_name
        if self.platform == "ios" and self.ios is not None:
            return self.ios.bundle_id
        if self.platform == "web" and self.web is not None:
            return self.web.origin or self.web.base_url
        return None
