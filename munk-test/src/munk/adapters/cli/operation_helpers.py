from __future__ import annotations

import os
import sys
from collections.abc import Callable
from typing import Any

import typer

from munk.adapters.cli.machine_io import (
    build_error_response,
    build_success_response,
    emit_json_response,
)
from munk.services.errors import OperationCancelledError
from munk.services.machine_contracts import ERROR_RUNTIME_ERROR, EXIT_OPERATION_CANCELLED
from munk.services.operations.launcher import launch_detached_operation
from munk.services.operations.models import OperationKind
from munk.services.operations.service import OperationCommandResult, OperationService, OperationTracker


def resolve_async_mode(*, wait: bool, detach: bool) -> bool:
    return detach or not wait


def run_operation_command(
    *,
    kind: OperationKind,
    command: str,
    request_json: dict[str, Any],
    app_id: str | None,
    plan_id: str | None,
    case_id: str | None,
    json_output: bool,
    wait: bool,
    detach: bool,
    execute: Callable[[OperationTracker], OperationCommandResult],
) -> tuple[OperationTracker, OperationCommandResult]:
    operation_service = OperationService()
    existing_tracker = operation_service.tracker_for_current_env()
    detached = resolve_async_mode(wait=wait, detach=detach)
    tracker = existing_tracker or operation_service.create_operation(
        kind=kind,
        request_json=request_json,
        app_id=app_id,
        plan_id=plan_id,
        case_id=case_id,
    )

    if detached and existing_tracker is None:
        launch_result = launch_detached_operation(
            argv=list(sys.argv[1:]),
            operation_id=tracker.operation_id,
            db_path=operation_service.registry.db_path,
        )
        tracker.append_event(
            event_type="operation_submitted",
            message="detached operation submitted",
            data={"pid": launch_result.pid},
        )
        tracker.update_artifacts({"launcher_log": str(launch_result.launcher_log_path)})
        tracker.update_progress(detached_pid=launch_result.pid)
        tracker.get_record()
        if json_output:
            emit_json_response(
                build_success_response(
                    command=command,
                    data={
                        "operation_id": tracker.operation_id,
                        "status": "queued",
                        "verification_verdict": None,
                    },
                    artifacts={"launcher_log": str(launch_result.launcher_log_path)},
                )
            )
        else:
            typer.echo(f"operation_id={tracker.operation_id}")
            typer.echo("status=queued")
            typer.echo(f"pid={launch_result.pid}")
        raise typer.Exit(code=0)

    tracker.mark_running(pid=os.getpid())
    tracker.append_event(
        event_type="operation_started",
        message="operation started",
        data={"pid": os.getpid(), "command": command},
    )
    try:
        result = execute(tracker)
    except OperationCancelledError:
        tracker.mark_cancelled()
        if json_output:
            emit_json_response(
                build_error_response(
                    command=command,
                    code="operation_cancelled",
                    message="operation cancelled cooperatively",
                    details={"operation_id": tracker.operation_id},
                )
            )
        else:
            typer.echo(f"operation_id={tracker.operation_id}")
            typer.echo("status=cancelled")
        raise typer.Exit(code=EXIT_OPERATION_CANCELLED)
    except Exception as exc:
        tracker.mark_failed(error_code=ERROR_RUNTIME_ERROR, error_message=str(exc))
        raise

    if tracker.cancel_observed or result.status == "cancelled":
        tracker.mark_cancelled(
            result_json=result.result_json or result.data,
            artifacts=_stringify_artifacts(result.artifacts),
        )
        if json_output:
            emit_json_response(
                build_success_response(
                    command=command,
                    data={
                        **result.data,
                        "operation_id": tracker.operation_id,
                        "status": "cancelled",
                        "verification_verdict": None,
                    },
                    artifacts=result.artifacts,
                )
            )
        else:
            typer.echo(f"operation_id={tracker.operation_id}")
            typer.echo("status=cancelled")
        raise typer.Exit(code=EXIT_OPERATION_CANCELLED)

    tracker.mark_succeeded(
        verification_verdict=result.verification_verdict,
        result_json=result.result_json or result.data,
        artifacts=_stringify_artifacts(result.artifacts),
    )
    if json_output:
        emit_json_response(
            build_success_response(
                command=command,
                data={
                    **result.data,
                    "operation_id": tracker.operation_id,
                    "status": "succeeded",
                    "verification_verdict": result.verification_verdict,
                },
                artifacts=result.artifacts,
            )
        )
        raise typer.Exit(code=result.exit_code)

    return tracker, result


def _stringify_artifacts(artifacts: dict[str, Any]) -> dict[str, str]:
    return {key: str(value) for key, value in artifacts.items()}
