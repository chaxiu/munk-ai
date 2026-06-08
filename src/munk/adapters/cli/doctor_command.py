from __future__ import annotations

import typer

from munk.services.doctor_service import DoctorService


def doctor_command() -> None:
    result = DoctorService().run()
    if not result.ok:
        for item in result.missing_items:
            typer.echo(item)
        raise typer.Exit(code=1)
    typer.echo(f"adb: {result.adb_path}")
    if result.perception_diagnostics is not None:
        typer.echo(f"perception provider: {result.perception_diagnostics.provider_name}")
        if result.perception_diagnostics.asset_root is not None:
            typer.echo(f"perception assets: {result.perception_diagnostics.asset_root}")
