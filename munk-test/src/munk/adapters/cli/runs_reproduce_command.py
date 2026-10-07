from __future__ import annotations

import typer

from munk.adapters.cli.machine_io import emit_json_response
from munk.services.machine_command_service import MachineCommandService


def runs_reproduce_command(*, operation_id: str, json_output: bool) -> None:
    response = MachineCommandService().reproduce_operation(operation_id=operation_id)
    if json_output:
        emit_json_response(response.payload)
        raise typer.Exit(code=response.exit_code)
    if response.payload["ok"] is False:
        typer.echo(response.payload["error"]["message"], err=True)
        raise typer.Exit(code=response.exit_code)

    payload = response.payload["data"]
    typer.echo(f"operation_id={payload['operation_id']}")
    typer.echo(f"artifact_manifest_path={payload.get('artifact_manifest_path')}")
    for item in payload.get("reproduction_entries", []):
        typer.echo(f"target_kind={item['target_kind']} request_file={item['request_file']}")
        typer.echo(f"command={item['command']}")
    raise typer.Exit(code=response.exit_code)
