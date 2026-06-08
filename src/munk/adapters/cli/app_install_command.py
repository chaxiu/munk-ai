from __future__ import annotations

from pathlib import Path

import typer

from munk.adapters.cli.machine_io import (
    build_success_response,
    emit_json_response,
    handle_cli_error,
    load_json_request,
    reject_mixed_request_file_usage,
)
from munk.adapters.shared.app_lifecycle import AppLifecycleService
from munk.adapters.shared.machine_requests import AppInstallRequest


def app_install_command(
    *,
    app_id: str | None = None,
    artifact_path: Path | None = None,
    platform: str | None = None,
    device_ref: str | None = None,
    package: str | None = None,
    bundle_id: str | None = None,
    base_url: str | None = None,
    origin: str | None = None,
    headless: bool = False,
    assets_root: Path | None = None,
    request_file: Path | None = None,
    json_output: bool = False,
) -> None:
    try:
        reject_mixed_request_file_usage(
            request_file=request_file,
            command_name="app install",
            allowed_mixed_keys={"assets_root"},
            provided_business_args={
                "app_id": app_id,
                "artifact_path": artifact_path,
                "platform": platform,
                "device_ref": device_ref,
                "package": package,
                "bundle_id": bundle_id,
                "base_url": base_url,
                "origin": origin,
                "headless": headless if headless else None,
                "assets_root": assets_root,
            },
        )
        if request_file is not None:
            request = load_json_request(request_file, AppInstallRequest)
            if assets_root is not None:
                request = request.model_copy(update={"assets_root": assets_root})
        else:
            if app_id is None or artifact_path is None:
                raise ValueError("app install requires --app-id and --artifact-path")
            request = AppInstallRequest(
                app_id=app_id,
                artifact_path=artifact_path,
                platform=platform,
                device_ref=device_ref,
                package=package,
                bundle_id=bundle_id,
                base_url=base_url,
                origin=origin,
                headless=headless,
                assets_root=assets_root,
            )
        result = AppLifecycleService().install(request)
        payload = build_success_response(
            command="app_install",
            data={
                "action": result.action,
                "app_id": result.app_id,
                "platform": result.platform,
                "device_ref": result.device_ref,
                "entry_identity": result.entry_identity,
                "artifact_path": result.artifact_path,
            },
        )
    except Exception as exc:
        handle_cli_error(command="app_install", exc=exc, json_output=json_output)

    if json_output:
        emit_json_response(payload)
        raise typer.Exit(code=0)
    typer.echo(f"action={payload['data']['action']}")
    typer.echo(f"app_id={payload['data']['app_id']}")
    typer.echo(f"platform={payload['data']['platform']}")
    typer.echo(f"device_ref={payload['data']['device_ref']}")
    typer.echo(f"entry_identity={payload['data']['entry_identity']}")
    typer.echo(f"artifact_path={payload['data']['artifact_path']}")
