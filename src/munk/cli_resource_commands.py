from __future__ import annotations

from pathlib import Path
from typing import Callable

import typer


def register_cli_resource_commands(
    *,
    apps_app: typer.Typer,
    plans_app: typer.Typer,
    cases_app: typer.Typer,
    devices_app: typer.Typer,
    apply_workspace_home: Callable[[], None],
    boot_log: Callable[[str], None],
) -> None:
    _register_apps_commands(
        apps_app=apps_app,
        apply_workspace_home=apply_workspace_home,
        boot_log=boot_log,
    )
    _register_plans_and_cases_commands(
        plans_app=plans_app,
        cases_app=cases_app,
        apply_workspace_home=apply_workspace_home,
        boot_log=boot_log,
    )
    _register_devices_commands(
        devices_app=devices_app,
        apply_workspace_home=apply_workspace_home,
        boot_log=boot_log,
    )


def _register_apps_commands(
    *,
    apps_app: typer.Typer,
    apply_workspace_home: Callable[[], None],
    boot_log: Callable[[str], None],
) -> None:
    @apps_app.command("list")
    def apps_list(
        platform: str | None = typer.Option(None, "--platform"),
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        apply_workspace_home()
        boot_log("apps list command invoked")
        from munk.adapters.cli.apps_list_command import apps_list_command

        apps_list_command(platform=platform, json_output=json_output)

    @apps_app.command("get")
    def apps_get(
        app_id: str = typer.Option(..., "--app-id"),
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        apply_workspace_home()
        boot_log("apps get command invoked")
        from munk.adapters.cli.apps_get_command import apps_get_command

        apps_get_command(app_id=app_id, json_output=json_output)

    @apps_app.command("create")
    def apps_create(
        request_file: Path = typer.Option(..., "--request-file"),
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        apply_workspace_home()
        boot_log("apps create command invoked")
        from munk.adapters.cli.apps_create_command import apps_create_command

        apps_create_command(request_file=request_file, json_output=json_output)

    @apps_app.command("update")
    def apps_update(
        app_id: str = typer.Option(..., "--app-id"),
        request_file: Path = typer.Option(..., "--request-file"),
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        apply_workspace_home()
        boot_log("apps update command invoked")
        from munk.adapters.cli.apps_update_command import apps_update_command

        apps_update_command(app_id=app_id, request_file=request_file, json_output=json_output)

    @apps_app.command("delete")
    def apps_delete(
        app_id: str = typer.Option(..., "--app-id"),
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        apply_workspace_home()
        boot_log("apps delete command invoked")
        from munk.adapters.cli.apps_delete_command import apps_delete_command

        apps_delete_command(app_id=app_id, json_output=json_output)

    @apps_app.command("candidates-list")
    def apps_candidates_list(
        app_id: str = typer.Option(..., "--app-id"),
        status: str | None = typer.Option(None, "--status"),
        candidate_id: str | None = typer.Option(None, "--candidate-id"),
        limit: int = typer.Option(20, "--limit", min=1, max=200),
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        apply_workspace_home()
        boot_log("apps candidates-list command invoked")
        from munk.adapters.cli.knowledge_candidates_list_command import knowledge_candidates_list_command

        knowledge_candidates_list_command(
            app_id=app_id,
            status=status,
            candidate_id=candidate_id,
            limit=limit,
            json_output=json_output,
        )

    @apps_app.command("candidates-approve")
    def apps_candidates_approve(
        app_id: str = typer.Option(..., "--app-id"),
        candidate_id: str = typer.Option(..., "--candidate-id"),
        reviewed_by: str | None = typer.Option(None, "--reviewed-by"),
        review_note: str | None = typer.Option(None, "--review-note"),
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        apply_workspace_home()
        boot_log("apps candidates-approve command invoked")
        from munk.adapters.cli.knowledge_candidates_approve_command import knowledge_candidates_approve_command

        knowledge_candidates_approve_command(
            app_id=app_id,
            candidate_id=candidate_id,
            reviewed_by=reviewed_by,
            review_note=review_note,
            json_output=json_output,
        )

    @apps_app.command("candidates-reject")
    def apps_candidates_reject(
        app_id: str = typer.Option(..., "--app-id"),
        candidate_id: str = typer.Option(..., "--candidate-id"),
        reviewed_by: str | None = typer.Option(None, "--reviewed-by"),
        review_note: str | None = typer.Option(None, "--review-note"),
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        apply_workspace_home()
        boot_log("apps candidates-reject command invoked")
        from munk.adapters.cli.knowledge_candidates_reject_command import knowledge_candidates_reject_command

        knowledge_candidates_reject_command(
            app_id=app_id,
            candidate_id=candidate_id,
            reviewed_by=reviewed_by,
            review_note=review_note,
            json_output=json_output,
        )


def _register_plans_and_cases_commands(
    *,
    plans_app: typer.Typer,
    cases_app: typer.Typer,
    apply_workspace_home: Callable[[], None],
    boot_log: Callable[[str], None],
) -> None:
    @plans_app.command("list")
    def plans_list(
        app_id: str | None = typer.Option(None, "--app-id"),
        source: str | None = typer.Option(None, "--source"),
        limit: int = typer.Option(20, "--limit", min=1, max=200),
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        apply_workspace_home()
        boot_log("plans list command invoked")
        from munk.adapters.cli.plans_list_command import plans_list_command

        plans_list_command(app_id=app_id, source=source, limit=limit, json_output=json_output)

    @plans_app.command("get")
    def plans_get(
        app_id: str = typer.Option(..., "--app-id"),
        plan_id: str = typer.Option(..., "--plan-id"),
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        apply_workspace_home()
        boot_log("plans get command invoked")
        from munk.adapters.cli.plans_get_command import plans_get_command

        plans_get_command(app_id=app_id, plan_id=plan_id, json_output=json_output)

    @plans_app.command("reorder-cases")
    def plans_reorder_cases(
        app_id: str = typer.Option(..., "--app-id"),
        plan_id: str = typer.Option(..., "--plan-id"),
        request_file: Path = typer.Option(..., "--request-file"),
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        apply_workspace_home()
        boot_log("plans reorder-cases command invoked")
        from munk.adapters.cli.plans_reorder_cases_command import plans_reorder_cases_command

        plans_reorder_cases_command(app_id=app_id, plan_id=plan_id, request_file=request_file, json_output=json_output)

    @cases_app.command("get")
    def cases_get(
        app_id: str = typer.Option(..., "--app-id"),
        plan_id: str = typer.Option(..., "--plan-id"),
        case_id: str = typer.Option(..., "--case-id"),
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        apply_workspace_home()
        boot_log("cases get command invoked")
        from munk.adapters.cli.cases_get_command import cases_get_command

        cases_get_command(app_id=app_id, plan_id=plan_id, case_id=case_id, json_output=json_output)

    @cases_app.command("add")
    def cases_add(
        app_id: str = typer.Option(..., "--app-id"),
        plan_id: str = typer.Option(..., "--plan-id"),
        request_file: Path = typer.Option(..., "--request-file"),
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        apply_workspace_home()
        boot_log("cases add command invoked")
        from munk.adapters.cli.cases_add_command import cases_add_command

        cases_add_command(app_id=app_id, plan_id=plan_id, request_file=request_file, json_output=json_output)

    @cases_app.command("replace")
    def cases_replace(
        app_id: str = typer.Option(..., "--app-id"),
        plan_id: str = typer.Option(..., "--plan-id"),
        case_id: str = typer.Option(..., "--case-id"),
        request_file: Path = typer.Option(..., "--request-file"),
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        apply_workspace_home()
        boot_log("cases replace command invoked")
        from munk.adapters.cli.cases_replace_command import cases_replace_command

        cases_replace_command(
            app_id=app_id,
            plan_id=plan_id,
            case_id=case_id,
            request_file=request_file,
            json_output=json_output,
        )

    @cases_app.command("delete")
    def cases_delete(
        app_id: str = typer.Option(..., "--app-id"),
        plan_id: str = typer.Option(..., "--plan-id"),
        case_id: str = typer.Option(..., "--case-id"),
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        apply_workspace_home()
        boot_log("cases delete command invoked")
        from munk.adapters.cli.cases_delete_command import cases_delete_command

        cases_delete_command(app_id=app_id, plan_id=plan_id, case_id=case_id, json_output=json_output)


def _register_devices_commands(
    *,
    devices_app: typer.Typer,
    apply_workspace_home: Callable[[], None],
    boot_log: Callable[[str], None],
) -> None:
    @devices_app.command("list")
    def devices_list(
        platform: str | None = typer.Option(None, "--platform"),
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        apply_workspace_home()
        boot_log("devices list command invoked")
        from munk.adapters.cli.devices_list_command import devices_list_command

        devices_list_command(platform=platform, json_output=json_output)

    @devices_app.command("state")
    def devices_state(
        device_ref: str = typer.Option(..., "--device-ref", "--serial"),
        platform: str | None = typer.Option(None, "--platform"),
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        apply_workspace_home()
        boot_log("devices state command invoked")
        from munk.adapters.cli.devices_state_command import devices_state_command

        devices_state_command(device_ref=device_ref, platform=platform, json_output=json_output)

    @devices_app.command("unlock")
    def devices_unlock(
        device_ref: str = typer.Option(..., "--device-ref", "--serial"),
        platform: str | None = typer.Option(None, "--platform"),
        strategy: str = typer.Option("swipe", "--strategy"),
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        apply_workspace_home()
        boot_log("devices unlock command invoked")
        from munk.adapters.cli.devices_unlock_command import devices_unlock_command

        devices_unlock_command(
            device_ref=device_ref,
            platform=platform,
            strategy=strategy,
            json_output=json_output,
        )
