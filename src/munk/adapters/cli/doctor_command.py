from __future__ import annotations

import typer

from munk.services.doctor_service import DoctorService


def doctor_command(*, fix: bool = False) -> None:
    on_progress = _echo_progress if fix else None
    if fix:
        typer.echo("applying auto-fixable runtime repairs...")
    result = DoctorService().run(fix=fix, on_progress=on_progress)
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


def _echo_progress(message: str) -> None:
    typer.echo(message)
