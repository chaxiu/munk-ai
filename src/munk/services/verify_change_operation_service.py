from __future__ import annotations

from collections.abc import Callable
from typing import Any

from munk.config import ResolvedConfig
from munk.execution.models import ChangeVerificationRequest
from munk.services.change_verification_service import ChangeVerificationService
from munk.services.events import RunEventSink
from munk.services.machine_contracts import EXIT_OK, verdict_exit_code
from munk.services.operations.command_helpers import (
    build_execution_artifacts,
    verdict_from_execution_status,
)
from munk.services.operations.service import OperationCommandResult, OperationTracker
from munk.services.plan_execution_service import PlanExecutionService
from munk.services.running.service import RunService
from munk.services.verify_change_event_payloads import build_verify_change_operation_progress_payload
from munk.services.verify_change_operation_payloads import build_verify_change_operation_result_payload


class VerifyChangeOperationService:
    def __init__(
        self,
        *,
        change_verification_service_factory: Callable[
            [ResolvedConfig, OperationTracker, Callable[[str, str | None, dict[str, Any]], None], RunEventSink | None],
            ChangeVerificationService,
        ]
        | None = None,
    ) -> None:
        self._change_verification_service_factory = (
            change_verification_service_factory or self._default_change_verification_service
        )

    def execute(
        self,
        *,
        tracker: OperationTracker,
        request: ChangeVerificationRequest,
        progress_callback: Callable[[str, str | None, dict[str, Any]], None] | None,
        resolved_config: ResolvedConfig,
        event_sink: RunEventSink | None,
    ) -> OperationCommandResult:
        def emit_verify_progress(event_type: str, message: str | None, data: dict[str, Any]) -> None:
            tracker.append_event(event_type=event_type, message=message, data=data)
            tracker.update_progress(**build_verify_change_operation_progress_payload(event_type, data))
            if progress_callback is not None:
                progress_callback(event_type, message, data)

        phased_result = self._change_verification_service_factory(
            resolved_config,
            tracker,
            emit_verify_progress,
            event_sink,
        ).verify_change(request)
        artifacts: dict[str, str] = {
            "plan": str(phased_result.plan_result.plan_path),
            "snapshot": str(phased_result.plan_result.snapshot_path),
        }
        verification_verdict = None
        exit_code = EXIT_OK
        if phased_result.execution_result is not None:
            artifacts.update(build_execution_artifacts(phased_result.execution_result))
            verification_verdict = verdict_from_execution_status(phased_result.execution_result.verification_status)
            exit_code = verdict_exit_code(verification_verdict)
        payload = build_verify_change_operation_result_payload(
            phased_result,
            artifacts=artifacts,
        )
        return OperationCommandResult(
            data=payload.to_command_data(),
            artifacts=artifacts,
            verification_verdict=None if tracker.cancel_observed else verification_verdict,
            result_json=payload.model_dump(mode="json"),
            status="cancelled" if tracker.cancel_observed else "succeeded",
            exit_code=exit_code,
        )

    @staticmethod
    def _default_change_verification_service(
        resolved_config: ResolvedConfig,
        tracker: OperationTracker,
        progress_callback: Callable[[str, str | None, dict[str, Any]], None],
        event_sink: RunEventSink | None,
    ) -> ChangeVerificationService:
        return ChangeVerificationService(
            resolved_config=resolved_config,
            plan_execution_service=PlanExecutionService(
                resolved_config=resolved_config,
                run_service_factory=lambda: RunService(
                    resolved_config=resolved_config,
                    event_sink=event_sink,
                    operation_tracker=tracker,
                ),
                operation_tracker=tracker,
            ),
            operation_tracker=tracker,
            progress_callback=progress_callback,
        )
