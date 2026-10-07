from __future__ import annotations

import typer
from typing import Literal, cast

from munk.adapters.cli.machine_io import build_success_response, emit_json_response, handle_cli_error
from munk.adapters.shared.device_control import DeviceControlService


def devices_unlock_command(
    *,
    device_ref: str,
    platform: str | None,
    strategy: str,
    json_output: bool,
) -> None:
    try:
        if strategy != "swipe":
            raise ValueError(f"unsupported device_unlock strategy '{strategy}'")
        result = DeviceControlService().unlock(
            device_ref=device_ref,
            platform=platform,
            strategy=cast(Literal["swipe"], "swipe"),
        )
        payload = build_success_response(
            command="device_unlock",
            data={
                "platform": result.platform,
                "device_ref": result.device_ref,
                "strategy": result.strategy,
                "success": result.success,
                "changed": result.changed,
                "message": result.message,
                "before": result.before.model_dump(mode="json"),
                "after": result.after.model_dump(mode="json"),
            },
        )
    except Exception as exc:
        handle_cli_error(command="device_unlock", exc=exc, json_output=json_output)
    if json_output:
        emit_json_response(payload)
        raise typer.Exit(code=0)
    typer.echo(f"device_ref={payload['data']['device_ref']}")
    typer.echo(f"strategy={payload['data']['strategy']}")
    typer.echo(f"success={payload['data']['success']}")
    typer.echo(f"changed={payload['data']['changed']}")
    typer.echo(f"message={payload['data']['message']}")
