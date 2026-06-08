from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from munk.adapters.shared.machine_requests import empty_runtime_overrides
from munk.app import AppTarget
from munk.execution.models import RuntimeOverrideValue
from munk.planning.models import empty_paths
from munk.services.operations.models import OperationKind, OperationStatus, VerificationVerdict
from munk.testing import TestCase

ReviewPlatform = Literal["android", "ios", "web"]
ReviewCaseType = Literal["best_practice", "bad_case", "review_checkpoint"]
RunSurface = Literal["run_center"]


class DoctorInput(BaseModel):
    pass


class DevicesListInput(BaseModel):
    platform: Literal["android", "ios", "web"] | None = Field(
        default=None,
        description="Optional platform filter for discovered devices.",
    )


class AppsListInput(BaseModel):
    platform: Literal["android", "ios", "web"] | None = Field(
        default=None,
        description="Optional platform filter for saved apps.",
    )


class AppsGetInput(BaseModel):
    app_id: str = Field(description="Application identifier to load.")


class PlansListInput(BaseModel):
    app_id: str | None = Field(default=None, description="Optional app identifier filter.")
    source: str | None = Field(default=None, description="Optional plan source filter.")
    limit: int = Field(default=20, ge=1, le=200, description="Maximum number of plans to return.")


class PlansGetInput(BaseModel):
    app_id: str = Field(description="Application identifier owning the plan.")
    plan_id: str = Field(description="Plan identifier to load.")


class PlanCreateInput(BaseModel):
    app_id: str = Field(description="Application identifier used to store the generated plan.")
    requirement_doc_path: Path = Field(description="Path to an existing requirement or PRD document in the workspace.")
    technical_doc_path: Path | None = Field(
        default=None,
        description="Optional path to an existing technical design document in the workspace.",
    )
    user_prompt: str | None = Field(default=None, description="Optional additional planning prompt.")
    artifact_path: Path | None = Field(default=None, description="Optional artifact output root.")
    assets_root: Path | None = Field(default=None, description="Optional assets root override.")
    artifact_url: str | None = Field(default=None, description="Optional artifact URL attached to the requirement.")
    auto_run: bool = Field(
        default=False,
        description="Whether to execute the generated plan immediately after planning. Leave false for the default review-first workflow.",
    )
    device_ref: str | None = Field(
        default=None,
        description="Optional target device reference used only when auto_run is true.",
    )
    package: str | None = Field(
        default=None,
        description="Android package name used to build the execution target when auto_run is true. The current V1 auto_run path expects Android execution inputs.",
    )
    runtime_overrides: dict[str, RuntimeOverrideValue] = Field(
        default_factory=empty_runtime_overrides,
        description="Optional runtime overrides forwarded to execution when auto_run is true.",
    )


class RunPlanInput(BaseModel):
    app_id: str = Field(description="Application identifier owning the plan.")
    plan_id: str = Field(description="Plan identifier to execute.")
    app_target: AppTarget | None = Field(
        default=None,
        description="Optional explicit app target. Use this when you already know the full target object.",
    )
    device_ref: str | None = Field(default=None, description="Optional target device reference.")
    package: str | None = Field(default=None, description="Android package name override.")
    bundle_id: str | None = Field(default=None, description="iOS bundle identifier override.")
    base_url: str | None = Field(default=None, description="Web base URL override.")
    origin: str | None = Field(default=None, description="Optional web origin override.")
    headless: bool = Field(default=False, description="Whether to launch the web runtime headlessly.")
    artifact_path: Path | None = Field(default=None, description="Optional artifact output root.")
    assets_root: Path | None = Field(default=None, description="Optional assets root override.")
    runtime_overrides: dict[str, RuntimeOverrideValue] = Field(
        default_factory=empty_runtime_overrides,
        description="Optional runtime overrides applied during execution.",
    )
    fail_fast: bool = Field(default=False, description="Whether to stop plan execution after the first failed case.")


class ReviewInput(BaseModel):
    app_id: str | None = Field(default=None, description="Optional app identifier associated with the review.")
    change_summary: str | None = Field(default=None, description="Optional concise summary of the code change.")
    changed_files: list[str] = Field(default_factory=list, description="Optional list of changed file paths.")
    diff_text: str | None = Field(default=None, description="Optional unified diff text to review.")
    requirement_doc_path: Path | None = Field(default=None, description="Optional requirement document path.")
    technical_doc_path: Path | None = Field(default=None, description="Optional technical design document path.")
    review_query: str | None = Field(default=None, description="Optional free-form review question or focus area.")
    platforms: list[ReviewPlatform] = Field(default_factory=list, description="Optional platform filters.")
    tags: list[str] = Field(default_factory=list, description="Optional review tag filters.")
    case_types: list[ReviewCaseType] = Field(default_factory=list, description="Optional knowledge base case-type filters.")
    artifact_path: Path | None = Field(default=None, description="Optional artifact output root.")


class VerifyChangeInput(BaseModel):
    app_id: str = Field(description="Application identifier associated with the change.")
    provided_cases: list[TestCase] = Field(
        default_factory=list,
        description="Optional explicit test cases. Leave empty for the default change-driven planning path.",
    )
    enable_plan_agent: bool = Field(
        default=False,
        description="Recommended default for V1 MCP. Generate verification cases from change context using the plan agent.",
    )
    auto_run: bool = Field(
        default=False,
        description="Whether to execute verification after planning. When true, also provide an execution target such as device_ref plus package, bundle_id, or base_url.",
    )
    change_summary: str | None = Field(default=None, description="Optional concise change summary.")
    changed_files: list[str] = Field(default_factory=list, description="Optional changed file paths.")
    diff_text: str | None = Field(default=None, description="Optional unified diff text.")
    review_orchestration_path: Path | None = Field(
        default=None,
        description="Optional review orchestration artifact path for the review-first chain. Leave unset by default because this is not the recommended V1 MCP flow yet.",
    )
    requirement_doc_path: Path | None = Field(
        default=None,
        description="Optional path to an existing requirement document in the workspace.",
    )
    technical_doc_path: Path | None = Field(
        default=None,
        description="Optional path to an existing technical design document in the workspace.",
    )
    previous_report_path: Path | None = Field(default=None, description="Optional previous report path.")
    previous_result_paths: list[Path] = Field(
        default_factory=empty_paths,
        description="Optional prior result paths used as extra evidence.",
    )
    app_target: AppTarget | None = Field(
        default=None,
        description="Optional explicit execution target. Preferred when the target is already known.",
    )
    device_ref: str | None = Field(default=None, description="Optional target device reference used only when auto_run is true.")
    artifact_path: Path | None = Field(default=None, description="Optional artifact output root.")
    assets_root: Path | None = Field(default=None, description="Optional assets root override.")
    runtime_overrides: dict[str, RuntimeOverrideValue] = Field(
        default_factory=empty_runtime_overrides,
        description="Optional runtime overrides forwarded to execution.",
    )
    package: str | None = Field(
        default=None,
        description="Android package name used to derive the execution target when auto_run is true.",
    )
    bundle_id: str | None = Field(
        default=None,
        description="iOS bundle identifier used to derive the execution target when auto_run is true.",
    )
    base_url: str | None = Field(
        default=None,
        description="Web base URL used to derive the execution target when auto_run is true.",
    )
    origin: str | None = Field(default=None, description="Optional web origin override.")
    headless: bool = Field(default=False, description="Whether to launch the web runtime headlessly.")


class RunsListInput(BaseModel):
    limit: int = Field(default=20, ge=1, le=100, description="Maximum number of operations to return.")
    status: OperationStatus | None = Field(default=None, description="Optional operation status filter.")
    kind: OperationKind | None = Field(default=None, description="Optional operation kind filter.")
    device_ref: str | None = Field(default=None, description="Optional exact device reference filter.")
    surface: RunSurface | None = Field(
        default=None,
        description="Optional surface filter. Use run_center to keep only user-facing run operations.",
    )
    verification_verdict: VerificationVerdict = Field(
        default=None,
        description="Optional verification verdict filter.",
    )
    platform: Literal["android", "ios", "web"] | None = Field(
        default=None,
        description="Optional inferred platform filter.",
    )
    query: str | None = Field(
        default=None,
        description="Optional substring query over operation id, title, target, and related identifiers.",
    )


class RunsGetInput(BaseModel):
    operation_id: str = Field(description="Operation identifier to inspect.")
