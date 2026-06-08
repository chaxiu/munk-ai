from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from munk.adapters.mcp.result_presenters import require_success_payload, submitted_operation_output
from munk.adapters.mcp.tool_models import (
    AppsGetInput,
    AppsListInput,
    DevicesListInput,
    DoctorInput,
    PlanCreateInput,
    PlansGetInput,
    PlansListInput,
    ReviewInput,
    RunPlanInput,
    RunsGetInput,
    RunsListInput,
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
from munk.adapters.shared.app_queries import get_app_detail_payload, list_apps_payload
from munk.adapters.shared.device_queries import list_devices_payload
from munk.adapters.shared.machine_requests import (
    PlanCliRequest,
    ReviewCliRequest,
    RunPlanCliRequest,
    VerifyChangeCliRequest,
)
from munk.adapters.shared.operation_presenters import build_operation_summary
from munk.adapters.shared.payload_models import OperationDetailData, OperationListData
from munk.adapters.shared.plan_queries import get_plan_payload, list_plans_payload
from munk.app_assets.service import AppAssetService
from munk.planning.index_store import PlanCaseIndexStore
from munk.planning.storage import PlanStore
from munk.services.app_target_resolver import resolve_app_target_for_execution
from munk.services.doctor_service import DoctorService
from munk.services.machine_command_service import MachineCommandService
from munk.services.operations.registry import OperationRegistry


class McpToolHandlers:
    def __init__(
        self,
        *,
        machine_service_factory: Callable[[], MachineCommandService],
        doctor_service_factory: Callable[[], DoctorService] | None = None,
        app_service_factory: Callable[[], AppAssetService] | None = None,
        plan_store_factory: Callable[[], PlanStore] | None = None,
        operation_registry_factory: Callable[[], OperationRegistry] | None = None,
        workspace_root: Callable[[], Path] | None = None,
    ) -> None:
        self._machine_service_factory = machine_service_factory
        self._doctor_service_factory = doctor_service_factory or DoctorService
        self._app_service_factory = app_service_factory or AppAssetService
        self._plan_store_factory = plan_store_factory or PlanStore
        self._operation_registry_factory = operation_registry_factory or OperationRegistry
        self._workspace_root = workspace_root or Path.cwd

    def doctor(self, request: DoctorInput) -> DoctorOutput:
        del request
        result = self._doctor_service_factory().run()
        missing_count = len(result.missing_items)
        provider_name = (
            result.perception_diagnostics.provider_name if result.perception_diagnostics is not None else None
        )
        asset_root = result.perception_diagnostics.asset_root if result.perception_diagnostics is not None else None
        summary = "doctor passed" if result.ok else f"doctor found {missing_count} issue(s)"
        return DoctorOutput(
            summary=summary,
            ok=result.ok,
            adb_path=str(result.adb_path),
            missing_items=list(result.missing_items),
            perception_provider=provider_name,
            perception_asset_root=str(asset_root) if asset_root is not None else None,
        )

    def devices_list(self, request: DevicesListInput) -> DevicesListOutput:
        data = list_devices_payload(request.platform)
        return DevicesListOutput(summary=f"found {len(data.items)} device(s)", data=data)

    def apps_list(self, request: AppsListInput) -> AppsListOutput:
        data = list_apps_payload(service=self._app_service_factory(), platform=request.platform)
        return AppsListOutput(summary=f"found {len(data.items)} app(s)", data=data)

    def apps_get(self, request: AppsGetInput) -> AppsGetOutput:
        data = get_app_detail_payload(service=self._app_service_factory(), app_id=request.app_id)
        return AppsGetOutput(
            summary=f"loaded app {data.profile.app_id} ({data.profile.platform})",
            data=data,
        )

    def plans_list(self, request: PlansListInput) -> PlansListOutput:
        data = list_plans_payload(
            index_store=PlanCaseIndexStore(self._plan_store_factory().root_dir),
            app_id=request.app_id,
            source=request.source,
            case_count_mode=None,
            limit=request.limit,
            offset=0,
            include_latest_run=False,
        )
        return PlansListOutput(summary=f"found {len(data.items)} plan(s)", data=data)

    def plans_get(self, request: PlansGetInput) -> PlansGetOutput:
        data = get_plan_payload(
            plan_store=self._plan_store_factory(),
            app_id=request.app_id,
            plan_id=request.plan_id,
        )
        return PlansGetOutput(summary=f"loaded plan {data.plan_id} with {data.case_count} case(s)", data=data)

    def runs_list(self, request: RunsListInput) -> RunsListOutput:
        items = self._operation_registry_factory().list_operations(
            limit=request.limit,
            status=request.status,
            kind=request.kind,
            device_ref=request.device_ref,
            surface=request.surface,
            verification_verdict=request.verification_verdict,
            platform=request.platform,
            query=request.query,
        )
        data = OperationListData(items=[build_operation_summary(item) for item in items])
        return RunsListOutput(summary=f"found {len(data.items)} operation(s)", data=data)

    def runs_get(self, request: RunsGetInput) -> RunsGetOutput:
        response = self._machine_service_factory().get_operation(operation_id=request.operation_id)
        data = require_success_payload(response, action_label="runs_get")
        return RunsGetOutput(
            summary=f"loaded operation {request.operation_id} with status={data.get('status')}",
            data=OperationDetailData.model_validate(data),
        )

    def plan_create(self, request: PlanCreateInput) -> SubmittedOperationOutput:
        cli_request = PlanCliRequest(**request.model_dump())
        response = self._machine_service_factory().submit_plan(
            request=cli_request.to_requirement_input(),
            plan_execution_request=cli_request.to_plan_execution_request() if cli_request.auto_run else None,
            wait=True,
            detach=False,
            detached_argv=None,
        )
        return submitted_operation_output(response, action_label="plan_create")

    def run_plan(self, request: RunPlanInput) -> SubmittedOperationOutput:
        cli_request = RunPlanCliRequest(**request.model_dump())
        response = self._machine_service_factory().submit_run_plan(
            request=cli_request.to_plan_execution_request(),
            wait=True,
            detach=False,
            detached_argv=None,
        )
        return submitted_operation_output(response, action_label="run_plan")

    def review(self, request: ReviewInput) -> SubmittedOperationOutput:
        cli_request = ReviewCliRequest(**request.model_dump())
        response = self._machine_service_factory().submit_review(
            request=cli_request,
            wait=True,
            detach=False,
            detached_argv=None,
        )
        return submitted_operation_output(response, action_label="review")

    def verify_change(self, request: VerifyChangeInput) -> SubmittedOperationOutput:
        payload = request.model_dump(exclude={"package", "bundle_id", "base_url", "origin", "headless"})
        if request.auto_run and request.app_target is None:
            payload["app_target"] = resolve_app_target_for_execution(
                app_id=request.app_id,
                assets_root=request.assets_root,
                app_target=None,
                package=request.package,
                bundle_id=request.bundle_id,
                base_url=request.base_url,
                origin=request.origin,
                headless=request.headless,
            )
        cli_request = VerifyChangeCliRequest(**payload)
        response = self._machine_service_factory().submit_verify_change(
            request=cli_request,
            wait=True,
            detach=False,
            detached_argv=None,
        )
        return submitted_operation_output(response, action_label="verify_change")
