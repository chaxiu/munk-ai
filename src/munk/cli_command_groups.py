from __future__ import annotations

from typing import Callable

import typer

from munk.cli_app_lifecycle_commands import register_cli_app_lifecycle_commands
from munk.cli_resource_commands import register_cli_resource_commands
from munk.cli_run_operation_commands import register_cli_run_operation_commands
from munk.cli_runs_data_commands import register_cli_runs_data_commands


def register_cli_command_groups(
    *,
    app_lifecycle_app: typer.Typer,
    run_app: typer.Typer,
    verify_app: typer.Typer,
    runs_app: typer.Typer,
    mcp_app: typer.Typer,
    data_app: typer.Typer,
    apps_app: typer.Typer,
    plans_app: typer.Typer,
    cases_app: typer.Typer,
    devices_app: typer.Typer,
    apply_workspace_home: Callable[[], None],
    boot_log: Callable[[str], None],
) -> None:
    register_cli_app_lifecycle_commands(
        app_lifecycle_app=app_lifecycle_app,
        apply_workspace_home=apply_workspace_home,
        boot_log=boot_log,
    )
    register_cli_run_operation_commands(
        run_app=run_app,
        verify_app=verify_app,
        apply_workspace_home=apply_workspace_home,
        boot_log=boot_log,
    )
    register_cli_runs_data_commands(
        runs_app=runs_app,
        mcp_app=mcp_app,
        data_app=data_app,
        apply_workspace_home=apply_workspace_home,
        boot_log=boot_log,
    )
    register_cli_resource_commands(
        apps_app=apps_app,
        plans_app=plans_app,
        cases_app=cases_app,
        devices_app=devices_app,
        apply_workspace_home=apply_workspace_home,
        boot_log=boot_log,
    )
