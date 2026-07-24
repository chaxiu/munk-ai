from __future__ import annotations

import typer

from munk.services.doctor_service import DoctorService


def doctor_command(*, fix: bool = False) -> None:
    result = DoctorService().run(fix=fix)
    if not result.ok:
        for item in result.missing_items:
            typer.echo(item)
        raise typer.Exit(code=1)
    typer.echo(f"adb: {result.adb_path}")
    if result.perception_diagnostics is not None:
        typer.echo(f"perception provider: {result.perception_diagnostics.provider_name}")
        if result.perception_diagnostics.asset_root is not None:
            typer.echo(f"perception assets: {result.perception_diagnostics.asset_root}")
    if result.playwright_diagnostics is not None:
        typer.echo(f"playwright chromium: {result.playwright_diagnostics.browsers_dir}")
        for note in result.playwright_diagnostics.notes:
            typer.echo(note)
