from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import Field

from munk.adapters.mcp.tool_handlers import McpToolHandlers
from munk.adapters.mcp.tool_models import (
    AppsGetInput,
    AppsListInput,
    DevicesListInput,
    DoctorInput,
    PlanCreateInput,
    PlansGetInput,
    PlansListInput,
    ReviewCaseType,
    ReviewInput,
    ReviewPlatform,
    RunPlanInput,
    RunsGetInput,
    RunsListInput,
    RunSurface,
    VerifyChangeInput,
)
from munk.adapters.mcp.tool_outputs import (
    AppsGetOutput,
    AppsListOutput,
    DevicesListOutput,
    DoctorOutput,
    PlansGetOutput,
    PlansListOutput,
    RunsGetOutput,
    RunsListOutput,
    SubmittedOperationOutput,
)
from munk.execution.models import RuntimeOverrideValue
from munk.services.operations.models import OperationKind, OperationStatus, VerificationVerdict

AppPlatform = Literal["android", "ios", "web"]


def register_mcp_tools(mcp: Any, handlers: McpToolHandlers) -> None:
    @mcp.tool(
        name="doctor",
        title="Doctor",
        description=(
            "Run runtime health checks for the current Munk environment.\n"
            "Use this before planning or execution when you need to verify local prerequisites.\n"
            "Returns structured health details including adb path and missing requirements.\n"
            "Does not modify assets or start a run."
        ),
        structured_output=True,
    )
    def doctor() -> DoctorOutput:
        return handlers.doctor(DoctorInput())

    @mcp.tool(
        name="devices_list",
        title="List Devices",
        description=(
            "List discovered local devices for a platform or across all supported runtimes.\n"
            "Use this when a run requires device selection or you need to inspect availability.\n"
            "Returns the canonical discovered device payload.\n"
            "Does not claim or reserve any device."
        ),
        structured_output=True,
    )
    def devices_list(
        platform: Annotated[
            AppPlatform | None,
            Field(description="Optional platform filter: android, ios, or web."),
        ] = None,
    ) -> DevicesListOutput:
        return handlers.devices_list(DevicesListInput(platform=platform))

    @mcp.tool(
        name="apps_list",
        title="List Apps",
        description=(
            "List saved Munk apps from the current assets root.\n"
            "Use this before plan or run operations when you need to discover app identifiers.\n"
            "Returns the canonical app list payload with plan and case counts.\n"
            "Does not create, update, or delete app assets."
        ),
        structured_output=True,
    )
    def apps_list(
        platform: Annotated[
            AppPlatform | None,
            Field(description="Optional platform filter: android, ios, or web."),
        ] = None,
    ) -> AppsListOutput:
        return handlers.apps_list(AppsListInput(platform=platform))

    @mcp.tool(
        name="apps_get",
        title="Get App",
        description=(
            "Load one saved app by app_id.\n"
            "Use this when you need the canonical app target and introduction content for later planning or execution.\n"
            "Returns the canonical app detail payload.\n"
            "Does not modify app assets."
        ),
        structured_output=True,
    )
    def apps_get(
        app_id: Annotated[str, Field(description="Application identifier to load.")],
    ) -> AppsGetOutput:
        return handlers.apps_get(AppsGetInput(app_id=app_id))

    @mcp.tool(
        name="plans_list",
        title="List Plans",
        description=(
            "List saved plans from the current assets root.\n"
            "Use this before run_plan when you need to discover plan identifiers.\n"
            "Returns the canonical plan list payload.\n"
            "Does not execute or modify any plan."
        ),
        structured_output=True,
    )
    def plans_list(
        app_id: Annotated[str | None, Field(description="Optional app identifier filter.")] = None,
        source: Annotated[str | None, Field(description="Optional plan source filter.")] = None,
        limit: Annotated[int, Field(description="Maximum number of plans to return.", ge=1, le=200)] = 20,
    ) -> PlansListOutput:
        return handlers.plans_list(PlansListInput(app_id=app_id, source=source, limit=limit))

    @mcp.tool(
        name="plans_get",
        title="Get Plan",
        description=(
            "Load one saved plan by app_id and plan_id.\n"
            "Use this when you need the canonical plan detail before review or execution.\n"
            "Returns the canonical plan detail payload.\n"
            "Does not execute or edit the plan."
        ),
        structured_output=True,
    )
    def plans_get(
        app_id: Annotated[str, Field(description="Application identifier owning the plan.")],
        plan_id: Annotated[str, Field(description="Plan identifier to load.")],
    ) -> PlansGetOutput:
        return handlers.plans_get(PlansGetInput(app_id=app_id, plan_id=plan_id))

    @mcp.tool(
        name="plan_create",
        title="Create Plan",
        description=(
            "Generate a requirement-driven plan from existing requirement and optional technical documents.\n"
            "Use this for the default review-first workflow when you want plan assets before any execution.\n"
            "Returns operation_id, phase, status, and related identifiers.\n"
            "Does not execute the plan unless auto_run is true, and the current V1 auto_run path expects Android execution inputs."
        ),
        structured_output=True,
    )
    def plan_create(
        app_id: Annotated[str, Field(description="Application identifier used to store the generated plan.")],
        requirement_doc_path: Annotated[
            Path,
            Field(description="Path to an existing requirement or PRD document in the workspace."),
        ],
        technical_doc_path: Annotated[
            Path | None,
            Field(description="Optional path to an existing technical design document in the workspace."),
        ] = None,
        user_prompt: Annotated[str | None, Field(description="Optional additional planning prompt.")] = None,
        artifact_path: Annotated[Path | None, Field(description="Optional artifact output root.")] = None,
        assets_root: Annotated[Path | None, Field(description="Optional assets root override.")] = None,
        artifact_url: Annotated[str | None, Field(description="Optional artifact URL attached to the requirement.")] = None,
        auto_run: Annotated[
            bool,
            Field(description="Whether to execute the generated plan immediately. Leave false for the default review-first workflow."),
        ] = False,
        device_ref: Annotated[
            str | None,
            Field(description="Optional target device reference used only when auto_run is true."),
        ] = None,
        package: Annotated[
            str | None,
            Field(description="Android package name used only when auto_run is true. The current V1 auto_run path expects Android execution inputs."),
        ] = None,
        runtime_overrides: Annotated[
            dict[str, RuntimeOverrideValue],
            Field(description="Optional runtime overrides forwarded to execution."),
        ] = Field(default_factory=dict),
    ) -> SubmittedOperationOutput:
        return handlers.plan_create(
            PlanCreateInput(
                app_id=app_id,
                requirement_doc_path=requirement_doc_path,
                technical_doc_path=technical_doc_path,
                user_prompt=user_prompt,
                artifact_path=artifact_path,
                assets_root=assets_root,
                artifact_url=artifact_url,
                auto_run=auto_run,
                device_ref=device_ref,
                package=package,
                runtime_overrides=runtime_overrides,
            )
        )

    @mcp.tool(
        name="run_plan",
        title="Run Plan",
        description=(
            "Execute an existing saved plan.\n"
            "Use this after a plan has been reviewed and approved for execution.\n"
            "Returns operation_id, phase, status, and related identifiers.\n"
            "Does not generate a new plan."
        ),
        structured_output=True,
    )
    def run_plan(
        app_id: Annotated[str, Field(description="Application identifier owning the plan.")],
        plan_id: Annotated[str, Field(description="Plan identifier to execute.")],
        device_ref: Annotated[str | None, Field(description="Optional target device reference.")] = None,
        package: Annotated[str | None, Field(description="Optional Android package override.")] = None,
        bundle_id: Annotated[str | None, Field(description="Optional iOS bundle identifier override.")] = None,
        base_url: Annotated[str | None, Field(description="Optional web base URL override.")] = None,
        origin: Annotated[str | None, Field(description="Optional web origin override.")] = None,
        headless: Annotated[bool, Field(description="Whether to launch the web runtime headlessly.")] = False,
        artifact_path: Annotated[Path | None, Field(description="Optional artifact output root.")] = None,
        assets_root: Annotated[Path | None, Field(description="Optional assets root override.")] = None,
        runtime_overrides: Annotated[
            dict[str, RuntimeOverrideValue],
            Field(description="Optional runtime overrides applied during execution."),
        ] = Field(default_factory=dict),
        fail_fast: Annotated[bool, Field(description="Whether to stop after the first failed case.")] = False,
    ) -> SubmittedOperationOutput:
        return handlers.run_plan(
            RunPlanInput(
                app_id=app_id,
                plan_id=plan_id,
                device_ref=device_ref,
                package=package,
                bundle_id=bundle_id,
                base_url=base_url,
                origin=origin,
                headless=headless,
                artifact_path=artifact_path,
                assets_root=assets_root,
                runtime_overrides=runtime_overrides,
                fail_fast=fail_fast,
            )
        )

    @mcp.tool(
        name="review",
        title="Review Change",
        description=(
            "Run standalone structured code review using Munk review knowledge and orchestration.\n"
            "Use this when you need review findings without generating or executing a verification plan.\n"
            "Returns operation_id, status, and related identifiers.\n"
            "Does not execute device-driven verification."
        ),
        structured_output=True,
    )
    def review(
        app_id: Annotated[str | None, Field(description="Optional app identifier associated with the review.")] = None,
        change_summary: Annotated[str | None, Field(description="Optional concise change summary.")] = None,
        changed_files: Annotated[list[str], Field(description="Optional changed file paths.")] = Field(default_factory=list),
        diff_text: Annotated[str | None, Field(description="Optional unified diff text.")] = None,
        requirement_doc_path: Annotated[Path | None, Field(description="Optional requirement document path.")] = None,
        technical_doc_path: Annotated[Path | None, Field(description="Optional technical design document path.")] = None,
        review_query: Annotated[str | None, Field(description="Optional free-form review question or focus area.")] = None,
        platforms: Annotated[list[ReviewPlatform], Field(description="Optional platform filters.")] = Field(default_factory=list),
        tags: Annotated[list[str], Field(description="Optional review tag filters.")] = Field(default_factory=list),
        case_types: Annotated[list[ReviewCaseType], Field(description="Optional knowledge base case-type filters.")] = Field(default_factory=list),
        artifact_path: Annotated[Path | None, Field(description="Optional artifact output root.")] = None,
    ) -> SubmittedOperationOutput:
        return handlers.review(
            ReviewInput(
                app_id=app_id,
                change_summary=change_summary,
                changed_files=changed_files,
                diff_text=diff_text,
                requirement_doc_path=requirement_doc_path,
                technical_doc_path=technical_doc_path,
                review_query=review_query,
                platforms=platforms,
                tags=tags,
                case_types=case_types,
                artifact_path=artifact_path,
            )
        )

    @mcp.tool(
        name="verify_change",
        title="Verify Change",
        description=(
            "Generate or execute change-driven verification for a code change.\n"
            "Recommended V1 path: set enable_plan_agent=true and provide change context such as changed_files, diff_text, or change_summary.\n"
            "Leave review_orchestration_path unset by default because that review-first artifact chain is not the recommended MCP flow yet.\n"
            "Returns operation_id, phase, status, and related identifiers.\n"
            "Does not execute a run unless auto_run is true, and auto_run requires an execution target."
        ),
        structured_output=True,
    )
    def verify_change(
        app_id: Annotated[str, Field(description="Application identifier associated with the change.")],
        enable_plan_agent: Annotated[
            bool,
            Field(description="Recommended default for V1 MCP. Generate verification cases from change context using the plan agent."),
        ] = False,
        auto_run: Annotated[
            bool,
            Field(description="Whether to execute verification after planning. When true, also provide an execution target such as device_ref plus package, bundle_id, or base_url."),
        ] = False,
        change_summary: Annotated[str | None, Field(description="Optional concise change summary.")] = None,
        changed_files: Annotated[list[str], Field(description="Optional changed file paths.")] = Field(default_factory=list),
        diff_text: Annotated[str | None, Field(description="Optional unified diff text.")] = None,
        review_orchestration_path: Annotated[
            Path | None,
            Field(description="Optional review orchestration artifact path for the review-first chain. Leave unset by default because this is not the recommended V1 MCP flow yet."),
        ] = None,
        requirement_doc_path: Annotated[
            Path | None,
            Field(description="Optional path to an existing requirement document in the workspace."),
        ] = None,
        technical_doc_path: Annotated[
            Path | None,
            Field(description="Optional path to an existing technical design document in the workspace."),
        ] = None,
        previous_report_path: Annotated[Path | None, Field(description="Optional previous report path.")] = None,
        previous_result_paths: Annotated[
            list[Path],
            Field(description="Optional prior result paths used as extra evidence."),
        ] = Field(default_factory=list),
        device_ref: Annotated[
            str | None,
            Field(description="Optional target device reference used only when auto_run is true."),
        ] = None,
        artifact_path: Annotated[Path | None, Field(description="Optional artifact output root.")] = None,
        assets_root: Annotated[Path | None, Field(description="Optional assets root override.")] = None,
        runtime_overrides: Annotated[
            dict[str, RuntimeOverrideValue],
            Field(description="Optional runtime overrides forwarded to execution."),
        ] = Field(default_factory=dict),
        package: Annotated[str | None, Field(description="Optional Android package name for auto_run execution.")] = None,
        bundle_id: Annotated[str | None, Field(description="Optional iOS bundle identifier for auto_run execution.")] = None,
        base_url: Annotated[str | None, Field(description="Optional web base URL for auto_run execution.")] = None,
        origin: Annotated[str | None, Field(description="Optional web origin override.")] = None,
        headless: Annotated[bool, Field(description="Whether to launch the web runtime headlessly.")] = False,
    ) -> SubmittedOperationOutput:
        return handlers.verify_change(
            VerifyChangeInput(
                app_id=app_id,
                enable_plan_agent=enable_plan_agent,
                auto_run=auto_run,
                change_summary=change_summary,
                changed_files=changed_files,
                diff_text=diff_text,
                review_orchestration_path=review_orchestration_path,
                requirement_doc_path=requirement_doc_path,
                technical_doc_path=technical_doc_path,
                previous_report_path=previous_report_path,
                previous_result_paths=previous_result_paths,
                device_ref=device_ref,
                artifact_path=artifact_path,
                assets_root=assets_root,
                runtime_overrides=runtime_overrides,
                package=package,
                bundle_id=bundle_id,
                base_url=base_url,
                origin=origin,
                headless=headless,
            )
        )

    @mcp.tool(
        name="runs_list",
        title="List Runs",
        description=(
            "List recorded operations from the local operation registry.\n"
            "Use this when you need to discover recent runs or filter by status, kind, platform, or device.\n"
            "Returns the canonical operation list payload.\n"
            "Does not start or modify any operation."
        ),
        structured_output=True,
    )
    def runs_list(
        limit: Annotated[int, Field(description="Maximum number of operations to return.", ge=1, le=100)] = 20,
        status: Annotated[
            OperationStatus | None,
            Field(description="Optional operation status filter: queued, running, succeeded, failed, or cancelled."),
        ] = None,
        kind: Annotated[
            OperationKind | None,
            Field(description="Optional operation kind filter such as plan, run_plan, verify_change, or review."),
        ] = None,
        device_ref: Annotated[str | None, Field(description="Optional exact device reference filter.")] = None,
        surface: Annotated[
            RunSurface | None,
            Field(description="Optional surface filter. Use run_center to keep only user-facing run operations."),
        ] = None,
        verification_verdict: Annotated[
            VerificationVerdict,
            Field(description="Optional verification verdict filter: passed, failed, or inconclusive."),
        ] = None,
        platform: Annotated[
            AppPlatform | None,
            Field(description="Optional inferred platform filter: android, ios, or web."),
        ] = None,
        query: Annotated[
            str | None,
            Field(description="Optional substring query over operation id, title, target, and related identifiers."),
        ] = None,
    ) -> RunsListOutput:
        return handlers.runs_list(
            RunsListInput(
                limit=limit,
                status=status,
                kind=kind,
                device_ref=device_ref,
                surface=surface,
                verification_verdict=verification_verdict,
                platform=platform,
                query=query,
            )
        )

    @mcp.tool(
        name="runs_get",
        title="Get Run",
        description=(
            "Load one recorded operation by operation_id.\n"
            "Use this to inspect current status, phase, summary, progress, and artifact metadata.\n"
            "Returns the canonical operation detail payload.\n"
            "Does not resume or rerun the operation."
        ),
        structured_output=True,
    )
    def runs_get(
        operation_id: Annotated[str, Field(description="Operation identifier to inspect.")],
    ) -> RunsGetOutput:
        return handlers.runs_get(RunsGetInput(operation_id=operation_id))
