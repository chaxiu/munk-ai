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
from munk.adapters.cli.run_event_printer import print_run_event
from munk.adapters.shared.machine_requests import RunCaseCliRequest, build_ios_app_target, build_web_app_target
from munk.app import AndroidAppIdentity, AppTarget
from munk.config.runtime import require_config_context
from munk.execution.models import PlanExecutionRequest
from munk.runtime import build_runtime_overrides_for_cli
from munk.services.machine_command_service import MachineCommandService


def run_case_command(
    *,
    app_id: str | None = None,
    plan_id: str | None = None,
    case_id: str | None = None,
    platform: str = "android",
    device_ref: str | None = None,
    package: str | None = None,
    bundle_id: str | None = None,
    base_url: str | None = None,
    origin: str | None = None,
    headless: bool = False,
    assets_root: Path | None = None,
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
    resolved_config = None
    try:
        reject_mixed_request_file_usage(
            request_file=request_file,
            command_name="run case",
            allowed_mixed_keys={"config", "assets_root"},
            provided_business_args={
                "app_id": app_id,
                "plan_id": plan_id,
                "case_id": case_id,
                "platform": platform if platform != "android" else None,
                "device_ref": device_ref,
                "package": package,
                "bundle_id": bundle_id,
                "base_url": base_url,
                "origin": origin,
                "headless": headless if headless else None,
                "assets_root": assets_root,
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
            request_payload: RunCaseCliRequest = load_json_request(request_file, RunCaseCliRequest)
            if assets_root is not None:
                request_payload = request_payload.model_copy(update={"assets_root": assets_root})
            request = request_payload.to_plan_execution_request()
            target_case_id = request_payload.case_id
        else:
            resolved_config = require_config_context(
                cli_path=config,
                workspace_root=Path.cwd(),
                command_name="run case",
            )
            if app_id is None or plan_id is None or case_id is None:
                raise ValueError("run case requires --app-id, --plan-id and --case-id")
            request = PlanExecutionRequest(
                app_id=app_id,
                plan_id=plan_id,
                app_target=_build_app_target(
                    app_id=app_id,
                    platform=platform,
                    package=package,
                    bundle_id=bundle_id,
                    base_url=base_url,
                    origin=origin,
                    headless=headless,
                ),
                device_ref=device_ref,
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
            target_case_id = case_id
    except Exception as exc:
        handle_cli_error(command="run_case", exc=exc, json_output=json_output)

    if resolved_config is None:
        resolved_config = require_config_context(
            cli_path=config,
            workspace_root=Path.cwd(),
            command_name="run case",
        )

    response = MachineCommandService(resolved_config=resolved_config).submit_run_case(
        request=request,
        case_id=target_case_id,
        wait=wait,
        detach=detach,
        detached_argv=list(sys.argv[1:]),
        event_sink=None if json_output else print_run_event,
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
    typer.echo(f"case_id={target_case_id}")
    typer.echo(f"verdict={data['verdict']}")
    typer.echo(f"execution_status={data['execution']['status']}")
    typer.echo(f"run_dir={data['run_dir']}")
    typer.echo(f"stop_reason={data['execution'].get('stop_reason')}")
    raise typer.Exit(code=response.exit_code)


def _build_app_target(
    *,
    app_id: str,
    platform: str,
    package: str | None,
    bundle_id: str | None,
    base_url: str | None,
    origin: str | None,
    headless: bool,
) -> AppTarget:
    normalized = platform.strip().lower()
    if normalized == "android":
        if not package:
            raise ValueError("android runtime currently requires package")
        return AppTarget(
            app_id=app_id,
            platform="android",
            android=AndroidAppIdentity(package_name=package),
        )
    if normalized == "web":
        return build_web_app_target(
            app_id=app_id,
            base_url=base_url,
            origin=origin,
            headless=headless,
        )
    if normalized == "ios":
        return build_ios_app_target(app_id=app_id, bundle_id=bundle_id)
    raise ValueError(f"unsupported run case platform: {platform}")
