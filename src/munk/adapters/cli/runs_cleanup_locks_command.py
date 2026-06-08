from __future__ import annotations

import typer

from munk.adapters.cli.machine_io import emit_json_response
from munk.services.machine_command_service import MachineCommandService


def runs_cleanup_locks_command(*, json_output: bool) -> None:
    response = MachineCommandService().cleanup_stale_claims()
    if json_output:
        emit_json_response(response.payload)
        raise typer.Exit(code=response.exit_code)
    if response.payload["ok"] is False:
        typer.echo(response.payload["error"]["message"], err=True)
        raise typer.Exit(code=response.exit_code)
    data = response.payload["data"]
    typer.echo(f"cleaned_count={data['cleaned_count']}")
    for item in data["items"]:
        typer.echo(
            " ".join(
                [
                    f"resource_key={item['resource_key']}",
                    f"action={item['action']}",
                    f"operation_id={item.get('operation_id')}",
                ]
            )
        )
    raise typer.Exit(code=response.exit_code)
