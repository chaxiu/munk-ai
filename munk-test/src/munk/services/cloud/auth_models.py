from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CloudUserSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    email: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None


class CloudSessionRecord(BaseModel):
    """Persisted Host session. Never expose tokens via Local API summaries."""

    model_config = ConfigDict(extra="ignore")

    access_token: str
    refresh_token: str
    expires_at: datetime | None = None
    user: CloudUserSummary
    cloud_base_url: str
    updated_at: datetime = Field(default_factory=utc_now)


class CloudSessionSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    authenticated: bool = False
    user: CloudUserSummary | None = None
    expires_at: datetime | None = None
    cloud_base_url: str | None = None
    can_refresh: bool = False


class CloudWorkspaceSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    slug: str
    name: str
    role: str


class CloudLoginStart(BaseModel):
    model_config = ConfigDict(extra="ignore")

    authorize_url: str
    state: str
    redirect_uri: str


class PendingCloudLogin(BaseModel):
    model_config = ConfigDict(extra="ignore")

    state: str
    redirect_uri: str
    cloud_base_url: str
    created_at: datetime = Field(default_factory=utc_now)


class CloudBffError(Exception):
    def __init__(self, *, status_code: int, code: str, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
