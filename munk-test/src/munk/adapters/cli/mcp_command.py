from __future__ import annotations

import typer

from munk.adapters.mcp.server import run_mcp_server


def mcp_command() -> None:
    typer.echo("mcp serve is a compatibility stdio entrypoint; prefer `munk serve` and HTTP `/mcp`.", err=True)
    run_mcp_server()
