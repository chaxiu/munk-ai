from __future__ import annotations

from pydantic import BaseModel, Field

from munk.adapters.shared.payload_models import (
    AppDetailData,
    AppListData,
    DeviceListData,
    OperationDetailData,
    OperationListData,
    PlanDetailData,
    PlanListData,
)


class SubmittedOperationOutput(BaseModel):
    summary: str = Field(description="Human-readable summary of the submitted operation result.")
    operation_id: str = Field(description="Operation identifier used to query later status.")
    status: str = Field(description="Current operation status such as queued, running, or succeeded.")
    phase: str | None = Field(default=None, description="Current operation phase when available.")
    app_id: str | None = Field(default=None, description="Associated app identifier when available.")
    plan_id: str | None = Field(default=None, description="Associated plan identifier when available.")
    verification_verdict: str | None = Field(
        default=None,
        description="Verification verdict when already known.",
    )


class DoctorOutput(BaseModel):
    summary: str = Field(description="Concise doctor result summary.")
    ok: bool = Field(description="Whether the runtime passed all doctor checks.")
    adb_path: str = Field(description="Resolved adb executable path.")
    missing_items: list[str] = Field(
        default_factory=list,
        description="Missing runtime requirements or health check failures.",
    )
    perception_provider: str | None = Field(
        default=None,
        description="Detected perception provider name when available.",
    )
    perception_asset_root: str | None = Field(
        default=None,
        description="Detected perception asset root when available.",
    )


class DevicesListOutput(BaseModel):
    summary: str = Field(description="Concise device list summary.")
    data: DeviceListData = Field(description="Canonical discovered device payload.")


class AppsListOutput(BaseModel):
    summary: str = Field(description="Concise app list summary.")
    data: AppListData = Field(description="Canonical app list payload.")


class AppsGetOutput(BaseModel):
    summary: str = Field(description="Concise app detail summary.")
    data: AppDetailData = Field(description="Canonical app detail payload.")


class PlansListOutput(BaseModel):
    summary: str = Field(description="Concise plan list summary.")
    data: PlanListData = Field(description="Canonical plan list payload.")


class PlansGetOutput(BaseModel):
    summary: str = Field(description="Concise plan detail summary.")
    data: PlanDetailData = Field(description="Canonical plan detail payload.")


class RunsListOutput(BaseModel):
    summary: str = Field(description="Concise operation list summary.")
    data: OperationListData = Field(description="Canonical operation list payload.")


class RunsGetOutput(BaseModel):
    summary: str = Field(description="Concise operation detail summary.")
    data: OperationDetailData = Field(description="Canonical operation detail payload.")
