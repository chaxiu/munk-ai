from __future__ import annotations

from pathlib import Path

import typer

from munk.services.annotate_service import AnnotateService
from munk.services.models import AnnotateRequest


def annotate_command(
    image: Path,
    output: Path | None,
    max_side: int,
    icon_conf: float,
) -> None:
    try:
        result = AnnotateService().run(
            AnnotateRequest(
                image_path=image,
                output_path=output,
                max_side=max_side,
                icon_conf=icon_conf,
            )
        )
    except FileNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"annotated: {result.output_path}")
    typer.echo(f"elements: {result.element_count}")
