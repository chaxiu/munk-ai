from __future__ import annotations

import typer

from munk.adapters.cli.machine_io import build_success_response, emit_json_response, handle_cli_error
from munk.adapters.shared.device_control import DeviceControlService


def devices_state_command(*, device_ref: str, platform: str | None, json_output: bool) -> None:
    try:
        result = DeviceControlService().get_state(device_ref=device_ref, platform=platform)
        payload = build_success_response(
            command="device_state",
            data=result.model_dump(mode="json"),
        )
    except Exception as exc:
        handle_cli_error(command="device_state", exc=exc, json_output=json_output)
    if json_output:
        emit_json_response(payload)
        raise typer.Exit(code=0)
    typer.echo(f"device_ref={payload['data']['device_ref']}")
    typer.echo(f"platform={payload['data']['platform']}")
    typer.echo(f"availability={payload['data']['availability']}")
    typer.echo(f"automation_ready={payload['data']['automation_ready']}")
    typer.echo(f"is_locked={payload['data']['is_locked']}")
    typer.echo(f"is_screen_on={payload['data']['is_screen_on']}")

