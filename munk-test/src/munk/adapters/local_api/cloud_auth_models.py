from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CloudUserSummaryData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    email: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None


class CloudSessionSummaryData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    authenticated: bool = False
    user: CloudUserSummaryData | None = None
    expires_at: datetime | None = None
    cloud_base_url: str | None = None
    can_refresh: bool = False


class CloudLoginStartData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    authorize_url: str
    state: str
    redirect_uri: str


class CloudWorkspaceSummaryData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    slug: str
    name: str
    role: str


class CloudWorkspacesData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    workspaces: list[CloudWorkspaceSummaryData] = Field(default_factory=list)
