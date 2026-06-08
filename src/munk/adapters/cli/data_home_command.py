from __future__ import annotations

import typer

from munk.adapters.cli.machine_io import emit_json_response
from munk.services.user_data_paths import describe_user_data_paths


def data_home_command(*, json_output: bool) -> None:
    payload = {
        "ok": True,
        "command": "data_home",
        "data": {
            "paths": describe_user_data_paths().to_json(),
        },
    }
    if json_output:
        emit_json_response(payload)
        raise typer.Exit(code=0)

    for key, value in payload["data"]["paths"].items():
        typer.echo(f"{key}={value}")
