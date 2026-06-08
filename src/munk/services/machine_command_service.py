from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from pathlib import Path
from typing import Any, cast

from munk.adapters.shared.machine_requests import RunPlansCliRequest
from munk.config import ResolvedConfig
from munk.config.runtime import require_config_context
from munk.execution.models import ChangeVerificationRequest, PlanExecutionRequest
from munk.planning.models import RequirementInput
from munk.planning.storage import PlanStore
from munk.reviewing.models import ReviewRequest
from munk.services.events import RunEventSink
from munk.services.machine_contracts import MachineCommandResponse
from munk.services.operations.query_service import OperationQueryService
from munk.services.operations.service import OperationService
from munk.services.operations.submission_service import OperationSubmissionService
from munk.services.plan_operation_service import PlanOperationService
from munk.services.review_operation_service import ReviewOperationService
from munk.services.running.batch_operation_service import RunBatchOperationService
from munk.services.running.operation_service import RunOperationService
from munk.services.verify_change_operation_service import VerifyChangeOperationService
from munk.telemetry import TelemetrySink, build_telemetry_service
from munk.telemetry.models import TelemetryEntrypoint


class MachineCommandService:
    def __init__(
        self,
        operation_service: OperationService | None = None,
        *,
        resolved_config: ResolvedConfig | None = None,
        workspace_root: Path | None = None,
        entrypoint: TelemetryEntrypoint = "cli",
        telemetry_service: TelemetrySink | None = None,
    ) -> None:
        self._operation_service = operation_service or OperationService()
        self._resolved_config = resolved_config
        self._workspace_root = workspace_root or Path.cwd()
        self._entrypoint = entrypoint
        self._telemetry = telemetry_service or build_telemetry_service(workspace_root=self._workspace_root)
        self._query_service = OperationQueryService(operation_service=self._operation_service)
        self._submission_service = OperationSubmissionService(
            operation_service=self._operation_service,
            query_service=self._query_service,
            telemetry=self._telemetry,
            entrypoint=self._entrypoint,
        )
        self._plan_operation_service = PlanOperationService()
        self._run_operation_service = RunOperationService()
        self._run_batch_operation_service = RunBatchOperationService(
            operation_service=self._operation_service,
            run_operation_service=self._run_operation_service,
        )
        self._verify_change_operation_service = VerifyChangeOperationService()
        self._review_operation_service = ReviewOperationService()

    def submit_plan(
        self,
        *,
        request: RequirementInput,
        plan_execution_request: PlanExecutionRequest | None = None,
        progress_callback: Callable[[str, str | None, dict[str, Any]], None] | None = None,
        wait: bool,
        detach: bool,
        detached_argv: list[str] | None = None,
        background_submitter: Callable[[str, Callable[[], None]], None] | None = None,
    ) -> MachineCommandResponse:
        resolved_config = self._require_resolved_config("plan")
        request_json = cast(dict[str, Any], request.model_dump(mode="json"))
        return self._submission_service.submit(
            kind="plan",
            command="plan",
            request_json=request_json,
            app_id=request.app_id,
            plan_id=None,
            case_id=None,
            requires_device=False,
            device_ref=None,
            wait=wait,
            detach=detach,
            detached_argv=detached_argv,
            background_submitter=background_submitter,
            execute=lambda tracker: self._plan_operation_service.execute(
                tracker=tracker,
                request=request,
                plan_execution_request=plan_execution_request,
                progress_callback=progress_callback,
                resolved_config=resolved_config,
            ),
        )

    def submit_run_case(
        self,
        *,
        request: PlanExecutionRequest,
        case_id: str,
        wait: bool,
        detach: bool,
        detached_argv: list[str] | None = None,
        event_sink: RunEventSink | None = None,
        background_submitter: Callable[[str, Callable[[], None]], None] | None = None,
    ) -> MachineCommandResponse:
        resolved_config = self._require_resolved_config("run case")
        request_payload = cast(dict[str, Any], request.model_dump(mode="json"))
        request_json: dict[str, Any] = {**request_payload, "case_id": case_id}
        case_title = self._load_case_title(app_id=request.app_id, plan_id=request.plan_id, case_id=case_id)
        if case_title is not None:
            request_json["case_title"] = case_title
        return self._submission_service.submit(
            kind="run_case",
            command="run_case",
            request_json=request_json,
            app_id=request.app_id,
            plan_id=request.plan_id,
            case_id=case_id,
            requires_device=True,
            device_ref=request.device_ref,
            wait=wait,
            detach=detach,
            detached_argv=detached_argv,
            background_submitter=background_submitter,
            execute=lambda tracker: self._run_operation_service.execute_case(
                tracker=tracker,
                request=request,
                case_id=case_id,
                resolved_config=resolved_config,
                event_sink=event_sink,
            ),
        )

    @staticmethod
    def _load_case_title(*, app_id: str, plan_id: str, case_id: str) -> str | None:
        try:
            plan = PlanStore().load(app_id, plan_id)
        except FileNotFoundError:
            return None
        case = next((item for item in plan.cases if item.case_id == case_id), None)
        if case is None:
            return None
        title = case.title.strip()
        return title or None

    def submit_run_plan(
        self,
        *,
        request: PlanExecutionRequest,
        wait: bool,
        detach: bool,
        detached_argv: list[str] | None = None,
        event_sink: RunEventSink | None = None,
        background_submitter: Callable[[str, Callable[[], None]], None] | None = None,
    ) -> MachineCommandResponse:
        resolved_config = self._require_resolved_config("run plan")
        request_json = cast(dict[str, Any], request.model_dump(mode="json"))
        return self._submission_service.submit(
            kind="run_plan",
            command="run_plan",
            request_json=request_json,
            app_id=request.app_id,
            plan_id=request.plan_id,
            case_id=None,
            requires_device=True,
            device_ref=request.device_ref,
            wait=wait,
            detach=detach,
            detached_argv=detached_argv,
            background_submitter=background_submitter,
            execute=lambda tracker: self._run_operation_service.execute_plan(
                tracker=tracker,
                request=request,
                resolved_config=resolved_config,
                event_sink=event_sink,
            ),
        )

    def submit_run_plans(
        self,
        *,
        request: RunPlansCliRequest,
        wait: bool,
        detach: bool,
        detached_argv: list[str] | None = None,
        background_submitter: Callable[[str, Callable[[], None]], None] | None = None,
    ) -> MachineCommandResponse:
        resolved_config = self._require_resolved_config("run plans")
        request_json = cast(dict[str, Any], request.model_dump(mode="json"))
        return self._submission_service.submit(
            kind="run_plans",
            command="run_plans",
            request_json=request_json,
            app_id=request.app_id,
            plan_id=None,
            case_id=None,
            requires_device=True,
            device_ref=request.device_ref,
            wait=wait,
            detach=detach,
            detached_argv=detached_argv,
            background_submitter=background_submitter,
            execute=lambda tracker: self._run_batch_operation_service.execute(
                tracker=tracker,
                request=request,
                resolved_config=resolved_config,
            ),
        )

    def submit_verify_change(
        self,
        *,
        request: ChangeVerificationRequest,
        progress_callback: Callable[[str, str | None, dict[str, Any]], None] | None = None,
        wait: bool,
        detach: bool,
        detached_argv: list[str] | None = None,
        event_sink: RunEventSink | None = None,
        background_submitter: Callable[[str, Callable[[], None]], None] | None = None,
    ) -> MachineCommandResponse:
        resolved_config = self._require_resolved_config("verify change")
        request_json = cast(dict[str, Any], request.model_dump(mode="json"))
        return self._submission_service.submit(
            kind="verify_change",
            command="verify_change",
            request_json=request_json,
            app_id=request.app_id,
            plan_id=None,
            case_id=None,
            requires_device=request.auto_run,
            device_ref=request.device_ref,
            wait=wait,
            detach=detach,
            detached_argv=detached_argv,
            background_submitter=background_submitter,
            execute=lambda tracker: self._verify_change_operation_service.execute(
                tracker=tracker,
                request=request,
                progress_callback=progress_callback,
                resolved_config=resolved_config,
                event_sink=event_sink,
            ),
        )

    def submit_review(
        self,
        *,
        request: ReviewRequest,
        wait: bool,
        detach: bool,
        detached_argv: list[str] | None = None,
        background_submitter: Callable[[str, Callable[[], None]], None] | None = None,
    ) -> MachineCommandResponse:
        resolved_config = self._require_resolved_config("review")
        request_json = cast(dict[str, Any], request.model_dump(mode="json"))
        return self._submission_service.submit(
            kind="review",
            command="review",
            request_json=request_json,
            app_id=request.app_id,
            plan_id=None,
            case_id=None,
            requires_device=False,
            device_ref=None,
            wait=wait,
            detach=detach,
            detached_argv=detached_argv,
            background_submitter=background_submitter,
            execute=lambda tracker: self._review_operation_service.execute(
                tracker=tracker,
                request=request,
                resolved_config=resolved_config,
            ),
        )

    def submit_optimize_case(
        self,
        *,
        request: Any,
        wait: bool,
        detach: bool,
        detached_argv: list[str] | None = None,
        parent_operation_id: str | None = None,
    ) -> MachineCommandResponse:
        request_json = cast(dict[str, Any], request.model_dump(mode="json"))
        optimize_service_class = cast(Any, import_module("munk.services.optimization.operation_service").OptimizeCaseOperationService)
        optimize_operation_service = optimize_service_class(
            resolved_config=self._require_resolved_config("optimize case")
        )
        return self._submission_service.submit(
            kind="optimize_case",
            command="optimize_case",
            request_json=request_json,
            app_id=request.app_id,
            plan_id=request.plan_id,
            case_id=request.case_id,
            requires_device=False,
            device_ref=None,
            wait=wait,
            detach=detach,
            detached_argv=detached_argv,
            parent_operation_id=parent_operation_id,
            reuse_current_tracker=False,
            execute=lambda tracker: optimize_operation_service.execute_command(
                tracker=tracker,
                request=request,
            ),
        )

    def get_operation(self, *, operation_id: str) -> MachineCommandResponse:
        return self._query_service.get_operation(operation_id=operation_id)

    def list_operation_events(
        self,
        *,
        operation_id: str,
        after_seq: int,
        limit: int,
    ) -> MachineCommandResponse:
        return self._query_service.list_operation_events(operation_id=operation_id, after_seq=after_seq, limit=limit)

    def get_operation_artifacts(self, *, operation_id: str) -> MachineCommandResponse:
        return self._query_service.get_operation_artifacts(operation_id=operation_id)

    def get_operation_children(self, *, operation_id: str) -> MachineCommandResponse:
        return self._query_service.get_operation_children(operation_id=operation_id)

    def cleanup_stale_claims(self) -> MachineCommandResponse:
        return self._query_service.cleanup_stale_claims()

    def cancel_operation(self, *, operation_id: str) -> MachineCommandResponse:
        return self._query_service.cancel_operation(operation_id=operation_id)

    def reproduce_operation(self, *, operation_id: str) -> MachineCommandResponse:
        return self._query_service.reproduce_operation(operation_id=operation_id)

    def _require_resolved_config(self, command_name: str) -> ResolvedConfig:
        if self._resolved_config is not None:
            return self._resolved_config
        return require_config_context(
            cli_path=None,
            workspace_root=self._workspace_root,
            command_name=command_name,
        )
