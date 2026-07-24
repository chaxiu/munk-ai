from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from munk.services.cloud.auth_models import utc_now


class CloudLink(BaseModel):
    """One linked workspace/app target for Local sync."""

    model_config = ConfigDict(extra="ignore")

    workspace_id: str
    app_id: str
    bound_at: datetime = Field(default_factory=utc_now)
    workspace_name: str | None = None
    role: str | None = None


# Backward-compatible alias used by older call sites during the rename.
CloudBinding = CloudLink


class CloudLinkSummary(BaseModel):
    """Link item plus local-only sync summary (no BFF round-trip)."""

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


class CloudLinksState(BaseModel):
    """Persisted linked apps list + active selection."""

    model_config = ConfigDict(extra="ignore")

    items: list[CloudLink] = Field(default_factory=list)
    active_app_id: str | None = None


class CloudLinksView(BaseModel):
    """API/service view of links with per-item local dirty summary."""

    model_config = ConfigDict(extra="ignore")

    items: list[CloudLinkSummary] = Field(default_factory=list)
    active_app_id: str | None = None


class CloudSyncState(BaseModel):
    """Local baseline after a successful pull/push."""

    model_config = ConfigDict(extra="ignore")

    workspace_id: str
    app_id: str
    base_revision: int = 0
    content_hash: str | None = None
    dirty: bool = False
    last_synced_at: datetime | None = None
    last_action: Literal["pull", "push", "force_push"] | None = None


class CloudAppSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    app_id: str
    app_name: str | None = None
    platform: str
    revision: int = 0
    content_hash: str | None = None
    updated_at: str | None = None


class CloudAppEnsureResult(BaseModel):
    """BFF ensure-app response (create shell or return existing)."""

    model_config = ConfigDict(extra="ignore")

    workspace_id: str
    app_id: str
    app_name: str | None = None
    platform: str
    revision: int = 0
    content_hash: str | None = None
    updated_at: str | None = None
    created: bool = False
    role: str = "member"
    can_push: bool = False
    can_force_push: bool = False


class CloudSyncStatus(BaseModel):
    """Merged cloud status + local sync_state / dirty."""

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


class CloudSyncPullResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    workspace_id: str
    app_id: str
    revision: int
    content_hash: str | None = None
    dirty: bool = False
    forced: bool = False
    plans_written: int = 0
    plans_deleted: int = 0


class CloudSyncPushResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    workspace_id: str
    app_id: str
    revision: int
    content_hash: str | None = None
    action: Literal["push", "force_push"] = "push"
    forced: bool = False


class CloudSyncPublishResult(BaseModel):
    """Result of ensure shell → bind → push."""

    model_config = ConfigDict(extra="ignore")

    workspace_id: str
    app_id: str
    revision: int
    content_hash: str | None = None
    action: Literal["push", "force_push"] = "push"
    forced: bool = False
    shell_created: bool = False


class AppSyncBundle(BaseModel):
    """Local mirror of BFF AppSyncBundle."""

    model_config = ConfigDict(extra="ignore")

    workspace_id: str
    app_id: str
    revision: int = 0
    content_hash: str | None = None
    app_profile: dict[str, Any]
    introduction: str | None = None
    knowledge_document: dict[str, Any] | None = None
    plans: list[dict[str, Any]] = Field(default_factory=list)
    team_config: dict[str, Any] = Field(default_factory=dict)


class LocalSyncConflictError(Exception):
    """Raised when local assets are dirty and cloud revision advanced."""

    def __init__(
        self,
        *,
        message: str,
        base_revision: int,
        cloud_revision: int,
        local_content_hash: str | None,
        cloud_content_hash: str | None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.base_revision = base_revision
        self.cloud_revision = cloud_revision
        self.local_content_hash = local_content_hash
        self.cloud_content_hash = cloud_content_hash
        self.code = "local_sync_conflict"

    def details(self) -> dict[str, Any]:
        return {
            "base_revision": self.base_revision,
            "cloud_revision": self.cloud_revision,
            "local_content_hash": self.local_content_hash,
            "cloud_content_hash": self.cloud_content_hash,
        }
