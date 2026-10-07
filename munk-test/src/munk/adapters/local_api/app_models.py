from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from munk.app import AndroidAppIdentity, AppPlatform, IOSAppIdentity, WebAppIdentity
from munk.app_assets.models import AppProfile, _default_introduction_ref, _default_knowledge_ref


class AppUpsertProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app_id: str
    app_name: str
    platform: AppPlatform
    app_introduction_ref: str = Field(default_factory=_default_introduction_ref)
    app_knowledge_ref: str = Field(default_factory=_default_knowledge_ref)
    android: AndroidAppIdentity | None = None
    ios: IOSAppIdentity | None = None
    web: WebAppIdentity | None = None

    @model_validator(mode="after")
    def validate_required_app_name(self) -> "AppUpsertProfile":
        self.app_name = self.app_name.strip()
        if not self.app_name:
            raise ValueError("app_name must not be empty")
        return self

    def to_profile(self) -> AppProfile:
        return AppProfile.model_validate(self.model_dump(mode="python"))


class AppUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: AppUpsertProfile
    introduction_markdown: str
    app_knowledge_file_name: str | None = None
    app_knowledge_content: str | None = None
