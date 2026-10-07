from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CloudLinkItemData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    workspace_id: str
    app_id: str
    bound_at: datetime
    workspace_name: str | None = None
    role: str | None = None
    dirty: bool = False
    base_revision: int | None = None
    last_synced_at: datetime | None = None
    last_action: Literal["pull", "push", "force_push"] | None = None


class CloudLinksData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    items: list[CloudLinkItemData] = Field(default_factory=list)
    active_app_id: str | None = None


class CloudLinkUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    workspace_id: str
    app_id: str
    workspace_name: str | None = None
    role: str | None = None


class CloudLinkData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    workspace_id: str
    app_id: str
    bound_at: datetime
    workspace_name: str | None = None
    role: str | None = None


class CloudLinkActiveRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    app_id: str


class CloudAppSummaryData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    app_id: str
    app_name: str | None = None
    platform: str
    revision: int = 0
    content_hash: str | None = None
    updated_at: str | None = None


class CloudAppsData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    workspace_id: str
    apps: list[CloudAppSummaryData] = Field(default_factory=list)


class CloudSyncStatusData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    workspace_id: str
    app_id: str
    revision: int = 0
    content_hash: str | None = None
    role: str
    can_pull: bool = True
    can_push: bool = False
    can_force_push: bool = False
    base_revision: int | None = None
    local_content_hash: str | None = None
    dirty: bool = False
    last_synced_at: datetime | None = None
    last_action: Literal["pull", "push", "force_push"] | None = None
    bound: bool = False


class CloudSyncPullRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    force: bool = False
    app_id: str | None = None


class CloudSyncPullResultData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    workspace_id: str
    app_id: str
    revision: int
    content_hash: str | None = None
    dirty: bool = False
    forced: bool = False
    plans_written: int = 0
    plans_deleted: int = 0


class CloudSyncPushRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    force: bool = False
    app_id: str | None = None


class CloudSyncPushResultData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    workspace_id: str
    app_id: str
    revision: int
    content_hash: str | None = None
    action: Literal["push", "force_push"] = "push"
    forced: bool = False


class CloudSyncPublishRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    workspace_id: str
    app_id: str
    workspace_name: str | None = None


class CloudSyncPublishResultData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    workspace_id: str
    app_id: str
    revision: int
    content_hash: str | None = None
    action: Literal["push", "force_push"] = "push"
    forced: bool = False
    shell_created: bool = False
