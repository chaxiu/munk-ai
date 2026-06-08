from __future__ import annotations

import typer

from munk.runtime import capture


def capture_command() -> None:
    typer.echo(f"capture placeholder: {capture()}")
