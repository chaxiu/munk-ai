from __future__ import annotations

import typer

from munk.adapters.cli.machine_io import emit_json_response
from munk.services.machine_command_service import MachineCommandService


def runs_events_command(
    *,
    operation_id: str,
    after_seq: int,
    limit: int,
    json_output: bool,
) -> None:
    response = MachineCommandService().list_operation_events(
        operation_id=operation_id,
        after_seq=after_seq,
        limit=limit,
    )
    if json_output:
        emit_json_response(response.payload)
        raise typer.Exit(code=response.exit_code)
    if response.payload["ok"] is False:
        typer.echo(response.payload["error"]["message"], err=True)
        raise typer.Exit(code=response.exit_code)

    payload = response.payload["data"]
    typer.echo(f"operation_id={operation_id}")
    for event in payload["items"]:
        typer.echo(
            f"{event['seq']} {event['timestamp']} {event['event_type']} {event.get('message') or ''}".strip()
        )
    raise typer.Exit(code=response.exit_code)
