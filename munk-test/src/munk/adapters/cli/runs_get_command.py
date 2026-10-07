from __future__ import annotations

import typer

from munk.adapters.cli.machine_io import emit_json_response
from munk.services.machine_command_service import MachineCommandService


def runs_get_command(*, operation_id: str, json_output: bool) -> None:
    response = MachineCommandService().get_operation(operation_id=operation_id)
    if json_output:
        emit_json_response(response.payload)
        raise typer.Exit(code=response.exit_code)
    if response.payload["ok"] is False:
        typer.echo(response.payload["error"]["message"], err=True)
        raise typer.Exit(code=response.exit_code)
    data = response.payload["data"]
    typer.echo(f"operation_id={data['operation_id']}")
    typer.echo(f"kind={data['kind']}")
    typer.echo(f"status={data['status']}")
    typer.echo(f"verification_verdict={data['verification_verdict']}")
    typer.echo(f"cancel_requested={data['cancel_requested']}")
    raise typer.Exit(code=response.exit_code)
