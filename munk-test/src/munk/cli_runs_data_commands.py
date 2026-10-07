from __future__ import annotations

from typing import Callable

import typer


def register_cli_runs_data_commands(
    *,
    runs_app: typer.Typer,
    mcp_app: typer.Typer,
    data_app: typer.Typer,
    apply_workspace_home: Callable[[], None],
    boot_log: Callable[[str], None],
) -> None:
    _register_runs_commands(
        runs_app=runs_app,
        apply_workspace_home=apply_workspace_home,
        boot_log=boot_log,
    )
    _register_mcp_commands(
        mcp_app=mcp_app,
        boot_log=boot_log,
    )
    _register_data_commands(
        data_app=data_app,
        apply_workspace_home=apply_workspace_home,
        boot_log=boot_log,
    )


def _register_runs_commands(
    *,
    runs_app: typer.Typer,
    apply_workspace_home: Callable[[], None],
    boot_log: Callable[[str], None],
) -> None:
    @runs_app.command("get")
    def runs_get(
        operation_id: str = typer.Option(..., "--operation-id"),
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        apply_workspace_home()
        boot_log("runs get command invoked")
        from munk.adapters.cli.runs_get_command import runs_get_command

        runs_get_command(operation_id=operation_id, json_output=json_output)

    @runs_app.command("events")
    def runs_events(
        operation_id: str = typer.Option(..., "--operation-id"),
        after_seq: int = typer.Option(0, "--after-seq"),
        limit: int = typer.Option(100, "--limit"),
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        apply_workspace_home()
        boot_log("runs events command invoked")
        from munk.adapters.cli.runs_events_command import runs_events_command

        runs_events_command(
            operation_id=operation_id,
            after_seq=after_seq,
            limit=limit,
            json_output=json_output,
        )

    @runs_app.command("artifacts")
    def runs_artifacts(
        operation_id: str = typer.Option(..., "--operation-id"),
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        apply_workspace_home()
        boot_log("runs artifacts command invoked")
        from munk.adapters.cli.runs_artifacts_command import runs_artifacts_command

        runs_artifacts_command(operation_id=operation_id, json_output=json_output)

    @runs_app.command("cancel")
    def runs_cancel(
        operation_id: str = typer.Option(..., "--operation-id"),
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        apply_workspace_home()
        boot_log("runs cancel command invoked")
        from munk.adapters.cli.runs_cancel_command import runs_cancel_command

        runs_cancel_command(operation_id=operation_id, json_output=json_output)

    @runs_app.command("reproduce")
    def runs_reproduce(
        operation_id: str = typer.Option(..., "--operation-id"),
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        apply_workspace_home()
        boot_log("runs reproduce command invoked")
        from munk.adapters.cli.runs_reproduce_command import runs_reproduce_command

        runs_reproduce_command(operation_id=operation_id, json_output=json_output)

    @runs_app.command("cleanup-locks")
    def runs_cleanup_locks(
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        apply_workspace_home()
        boot_log("runs cleanup-locks command invoked")
        from munk.adapters.cli.runs_cleanup_locks_command import runs_cleanup_locks_command

        runs_cleanup_locks_command(json_output=json_output)


def _register_mcp_commands(
    *,
    mcp_app: typer.Typer,
    boot_log: Callable[[str], None],
) -> None:
    @mcp_app.command("serve")
    def mcp_serve() -> None:
        boot_log("mcp serve command invoked")
        from munk.adapters.cli.mcp_command import mcp_command

        mcp_command()


def _register_data_commands(
    *,
    data_app: typer.Typer,
    apply_workspace_home: Callable[[], None],
    boot_log: Callable[[str], None],
) -> None:
    @data_app.command("home")
    def data_home(
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        apply_workspace_home()
        boot_log("data home command invoked")
        from munk.adapters.cli.data_home_command import data_home_command

        data_home_command(json_output=json_output)

    @data_app.command("search-cases")
    def data_search_cases(
        app_id: str | None = typer.Option(None, "--app-id"),
        plan_id: str | None = typer.Option(None, "--plan-id"),
        case_id: str | None = typer.Option(None, "--case-id"),
        is_core_case: bool | None = typer.Option(None, "--is-core-case"),
        start_mode: str | None = typer.Option(None, "--start-mode"),
        limit: int = typer.Option(20, "--limit", min=1, max=100),
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        apply_workspace_home()
        boot_log("data search-cases command invoked")
        from munk.adapters.cli.data_search_cases_command import data_search_cases_command

        data_search_cases_command(
            app_id=app_id,
            plan_id=plan_id,
            case_id=case_id,
            is_core_case=is_core_case,
            start_mode=start_mode,
            limit=limit,
            json_output=json_output,
        )

    @data_app.command("rebuild-case-index")
    def data_rebuild_case_index(
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        apply_workspace_home()
        boot_log("data rebuild-case-index command invoked")
        from munk.adapters.cli.data_rebuild_case_index_command import data_rebuild_case_index_command

        data_rebuild_case_index_command(json_output=json_output)
