from __future__ import annotations

import typer

from munk.adapters.cli.machine_io import build_success_response, emit_json_response, handle_cli_error
from munk.app_assets.service import AppAssetService
from munk.services.machine_contracts import InvalidMachineRequestError


def apps_delete_command(*, app_id: str, json_output: bool) -> None:
    try:
        service = AppAssetService()
        if not service.app_registry.exists(app_id):
            raise InvalidMachineRequestError(f"app '{app_id}' not found")
        service.assert_app_deletable(app_id)
        service.app_registry.delete(app_id)
        payload = build_success_response(command="apps_delete", data={"app_id": app_id})
    except Exception as exc:
        handle_cli_error(command="apps_delete", exc=exc, json_output=json_output)
    if json_output:
        emit_json_response(payload)
        raise typer.Exit(code=0)
    typer.echo(f"app_id={app_id}")
    typer.echo("status=deleted")
