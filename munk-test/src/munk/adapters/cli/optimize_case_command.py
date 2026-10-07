from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path
from typing import Any, cast

import typer

from munk.adapters.cli.machine_io import emit_json_response, handle_cli_error, load_json_request
from munk.config.runtime import require_config_context
from munk.services.machine_command_service import MachineCommandService


def optimize_case_command(
    *,
    request_file: Path,
    config: Path | None = None,
    json_output: bool = False,
    wait: bool = True,
    detach: bool = False,
) -> None:
    try:
        request_model = cast(Any, import_module("munk.services.optimization.request_models").OptimizeCaseOperationRequest)
        request = load_json_request(request_file, request_model)
        resolved_config = require_config_context(
            cli_path=config,
            workspace_root=Path.cwd(),
            command_name="optimize case",
        )
    except Exception as exc:
        handle_cli_error(command="optimize_case", exc=exc, json_output=json_output)

    response = MachineCommandService(resolved_config=resolved_config).submit_optimize_case(
        request=request,
        wait=wait,
        detach=detach,
        detached_argv=list(sys.argv[1:]),
        parent_operation_id=request.parent_operation_id,
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
    typer.echo(f"case_id={request.case_id}")
    if "summary" in data:
        typer.echo(f"summary={data['summary']}")
    raise typer.Exit(code=response.exit_code)
