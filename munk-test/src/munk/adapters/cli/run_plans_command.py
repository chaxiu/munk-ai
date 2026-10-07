from __future__ import annotations

import sys
from pathlib import Path

import typer

from munk.adapters.cli.machine_io import emit_json_response, handle_cli_error, load_json_request
from munk.adapters.shared.machine_requests import RunPlansCliRequest
from munk.config.runtime import require_config_context
from munk.services.machine_command_service import MachineCommandService


def run_plans_command(
    *,
    request_file: Path,
    config: Path | None = None,
    assets_root: Path | None = None,
    json_output: bool = False,
    wait: bool = True,
    detach: bool = False,
) -> None:
    try:
        request = load_json_request(request_file, RunPlansCliRequest)
        if assets_root is not None:
            request = request.model_copy(update={"assets_root": assets_root})
    except Exception as exc:
        handle_cli_error(command="run_plans", exc=exc, json_output=json_output)

    resolved_config = require_config_context(
        cli_path=config,
        workspace_root=Path.cwd(),
        command_name="run plans",
    )
    response = MachineCommandService(resolved_config=resolved_config).submit_run_plans(
        request=request,
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
    data = response.payload["data"]
    typer.echo(f"operation_id={data['operation_id']}")
    typer.echo(f"operation_status={data['status']}")
    typer.echo(f"completed_children={data['completed_children']}")
    typer.echo(f"total_children={data['total_children']}")
    raise typer.Exit(code=response.exit_code)
