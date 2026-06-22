from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, model_validator

from munk.app import AndroidAppIdentity, AppPlatform, AppTarget, IOSAppIdentity, WebAppIdentity


def _default_introduction_ref() -> str:
    return "introduction.md"


def _default_knowledge_ref() -> str:
    return "app_knowledge.json"


_APP_ID_PATTERN = re.compile(r"^[a-z0-9._-]+$")


def normalize_app_id(app_id: str) -> str:
    normalized = app_id.strip().lower()
    if not normalized:
        raise ValueError("app_id must not be empty")
    if any(part in {"..", "."} for part in normalized.split("/")):
        raise ValueError("app_id must not contain relative path segments")
    if "/" in normalized or "\\" in normalized:
        raise ValueError("app_id must not contain path separators")
    if not _APP_ID_PATTERN.fullmatch(normalized):
        raise ValueError("app_id must match [a-z0-9._-]+")
    return normalized


class AppProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    app_id: str
    app_name: str | None = None
    platform: AppPlatform
    app_introduction_ref: str = Field(default_factory=_default_introduction_ref)
    app_knowledge_ref: str = Field(default_factory=_default_knowledge_ref)
    android: AndroidAppIdentity | None = None
    ios: IOSAppIdentity | None = None
    web: WebAppIdentity | None = None

    @model_validator(mode="after")
    def validate_profile(self) -> "AppProfile":
        self.app_id = normalize_app_id(self.app_id)
        if self.app_name is not None:
            self.app_name = self.app_name.strip() or None
        identities: dict[str, AndroidAppIdentity | IOSAppIdentity | WebAppIdentity | None] = {
            "android": self.android,
            "ios": self.ios,
            "web": self.web,
        }
        active = [name for name, value in identities.items() if value is not None]
        if active != [self.platform]:
            raise ValueError(
                f"app profile for platform '{self.platform}' must define only '{self.platform}' identity details"
            )
        if not self.app_introduction_ref.strip():
            raise ValueError("app_introduction_ref must not be empty")
        if not self.app_knowledge_ref.strip():
            raise ValueError("app_knowledge_ref must not be empty")
        if self.platform == "web" and (self.web is None or not (self.web.base_url or "").strip()):
            raise ValueError("web app profile requires web.base_url")
        return self

    @property
    def entry_identity(self) -> str | None:
        return self.to_app_target().entry_identity

    def identity_label(self) -> str:
        if self.platform == "android" and self.android is not None:
            return f"Package: {self.android.package_name}"
        if self.platform == "ios" and self.ios is not None:
            return f"Bundle ID: {self.ios.bundle_id}"
        if self.platform == "web" and self.web is not None:
            if self.web.origin:
                return f"Origin: {self.web.origin}"
            if self.web.base_url:
                return f"Base URL: {self.web.base_url}"
        return "Entry Identity: none"

    def to_app_target(self) -> AppTarget:
        launch_context: dict[str, str] = {}
        if self.platform == "ios" and self.ios is not None:
            raw_wda_bundle_id = self.ios.wda_bundle_id
            if isinstance(raw_wda_bundle_id, str):
                wda_bundle_id = raw_wda_bundle_id.strip()
                if wda_bundle_id:
                    launch_context["wda_bundle_id"] = wda_bundle_id
        return AppTarget(
            app_id=self.app_id,
            platform=self.platform,
            launch_context=launch_context,
            android=self.android,
            ios=self.ios,
            web=self.web,
        )
