from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import typer

from munk.adapters.cli.machine_io import (
    emit_json_response,
    handle_cli_error,
    load_json_request,
    reject_mixed_request_file_usage,
)
from munk.adapters.shared.machine_requests import PlanCliRequest
from munk.app import AndroidAppIdentity, AppTarget
from munk.config.runtime import require_config_context
from munk.execution.models import PlanExecutionRequest
from munk.planning.models import RequirementInput
from munk.runtime import build_runtime_overrides_for_cli
from munk.services.machine_command_service import MachineCommandService


def plan_command(
    app_id: str | None = None,
    requirement_doc: Path | None = None,
    technical_doc: Path | None = None,
    device_ref: str | None = None,
    package: str | None = None,
    artifact_path: Path | None = None,
    assets_root: Path | None = None,
    artifact_url: str | None = None,
    auto_run: bool = False,
    max_steps: int | None = None,
    max_seconds: float | None = None,
    interval: float | None = None,
    max_side: int | None = None,
    icon_conf: float | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    vl_max_side: int | None = None,
    config: Path | None = None,
    request_file: Path | None = None,
    json_output: bool = False,
    wait: bool = True,
    detach: bool = False,
) -> None:
    execution_request: PlanExecutionRequest | None = None
    try:
        reject_mixed_request_file_usage(
            request_file=request_file,
            command_name="plan",
            allowed_mixed_keys={"config", "assets_root"},
            provided_business_args={
                "app_id": app_id,
                "requirement_doc": requirement_doc,
                "technical_doc": technical_doc,
                "device_ref": device_ref,
                "package": package,
                "artifact_path": artifact_path,
                "assets_root": assets_root,
                "artifact_url": artifact_url,
                "auto_run": True if auto_run else None,
                "max_steps": max_steps,
                "max_seconds": max_seconds,
                "interval": interval,
                "max_side": max_side,
                "icon_conf": icon_conf,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "vl_max_side": vl_max_side,
                "config": config,
            },
        )
        if request_file is not None:
            request_payload = load_json_request(request_file, PlanCliRequest)
            if assets_root is not None:
                request_payload = request_payload.model_copy(update={"assets_root": assets_root})
            plan_request = request_payload.to_requirement_input()
            execution_request = request_payload.to_plan_execution_request() if request_payload.auto_run else None
        else:
            if app_id is None or requirement_doc is None:
                raise ValueError("plan requires --app-id and --requirement-doc")
            plan_request = RequirementInput(
                app_id=app_id,
                requirement_doc_path=requirement_doc,
                technical_doc_path=technical_doc,
                artifact_path=artifact_path,
                assets_root=assets_root,
                artifact_url=artifact_url,
                auto_run=auto_run,
            )
    except Exception as exc:
        handle_cli_error(command="plan", exc=exc, json_output=json_output)

    resolved_config = require_config_context(
        cli_path=config,
        workspace_root=Path.cwd(),
        command_name="plan",
    )
    if request_file is None and auto_run:
        if app_id is None:
            raise AssertionError("app_id should be available when auto_run is enabled")
        execution_request = PlanExecutionRequest(
            app_id=app_id,
            plan_id="",
            app_target=_build_android_app_target(app_id=app_id, package=package),
            device_ref=device_ref,
            artifact_path=artifact_path,
            assets_root=assets_root,
            runtime_overrides=build_runtime_overrides_for_cli(
                resolved_config,
                max_steps=max_steps,
                max_seconds=max_seconds,
                interval=interval,
                max_side=max_side,
                icon_conf=icon_conf,
                max_tokens=max_tokens,
                temperature=temperature,
                vl_max_side=vl_max_side,
            ),
        )

    response = MachineCommandService(resolved_config=resolved_config).submit_plan(
        request=plan_request,
        plan_execution_request=execution_request,
        progress_callback=_stderr_plan_progress if (wait and not detach and not json_output) else None,
        wait=wait,
        detach=detach,
        detached_argv=list(sys.argv[1:]),
    )
    if json_output:
        emit_json_response(response.payload)
        raise typer.Exit(code=response.exit_code)
    if response.payload["ok"] is False:
        typer.echo(response.payload["error"]["message"], err=True)
        raise typer.Exit(code=response.exit_code)

    data: dict[str, Any] = response.payload["data"]
    typer.echo(f"operation_id={data['operation_id']}")
    typer.echo(f"operation_status={data['status']}")
    typer.echo(f"plan_id={data['plan_id']}")
    typer.echo(f"app_id={data['app_id']}")
    typer.echo(f"phase={data['phase']}")
    plan_result = data["plan_result"]
    typer.echo(f"cases={plan_result['case_count']}")
    typer.echo(f"plan_path={plan_result['plan_path']}")
    typer.echo(f"snapshot_path={plan_result['snapshot_path']}")
    execution_result = data.get("execution_result")
    if execution_result is not None:
        typer.echo(f"verification_status={execution_result['verification_status']}")
        typer.echo(f"total_cases={execution_result['total_cases']}")
        typer.echo(f"passed_cases={execution_result['passed_cases']}")
        typer.echo(f"failed_cases={execution_result['failed_cases']}")
        typer.echo(f"inconclusive_cases={execution_result['inconclusive_cases']}")
        typer.echo(f"stopped_early={execution_result['stopped_early']}")
        typer.echo(f"summary_path={execution_result['summary_path']}")
        typer.echo(f"report_path={execution_result['report_path']}")
    raise typer.Exit(code=response.exit_code)


def _build_android_app_target(*, app_id: str, package: str | None) -> AppTarget:
    if not package:
        raise ValueError("android runtime currently requires package when --auto-run is enabled")
    return AppTarget(
        app_id=app_id,
        platform="android",
        android=AndroidAppIdentity(package_name=package),
    )


def _stderr_plan_progress(event_type: str, message: str | None, data: dict[str, Any]) -> None:
    del event_type
    completed = data.get("completed_case_count")
    target = data.get("target_case_count")
    case_index = data.get("case_index")
    case_title = data.get("case_title")
    plan_id = data.get("plan_id")
    if case_index is not None and target is not None:
        prefix = f"[plan] case {case_index}/{target}"
        if case_title:
            typer.echo(f"{prefix}: {case_title}", err=True)
            return
        typer.echo(f"{prefix}: {message or 'working'}", err=True)
        return
    if completed is not None and target is not None:
        typer.echo(f"[plan] progress {completed}/{target}: {message or 'working'}", err=True)
        return
    if plan_id is not None and data.get("plan_path"):
        typer.echo(f"[plan] {message or 'plan saved'}: plan_id={plan_id}", err=True)
        return
    typer.echo(f"[plan] {message or 'working'}", err=True)
