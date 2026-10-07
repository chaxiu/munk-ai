from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import typer


def register_cli_run_operation_commands(
    *,
    run_app: typer.Typer,
    verify_app: typer.Typer,
    apply_workspace_home: Callable[[], None],
    boot_log: Callable[[str], None],
) -> None:
    @run_app.command("case")
    def run_case(
        app_id: str | None = typer.Option(None, "--app-id"),
        plan_id: str | None = typer.Option(None, "--plan-id"),
        case_id: str | None = typer.Option(None, "--case-id"),
        platform: str = typer.Option("android", "--platform"),
        device_ref: str | None = typer.Option(None, "--device-ref", "--serial"),
        package: str | None = typer.Option(None, "--package"),
        bundle_id: str | None = typer.Option(None, "--bundle-id"),
        base_url: str | None = typer.Option(None, "--base-url"),
        origin: str | None = typer.Option(None, "--origin"),
        headless: bool = typer.Option(False, "--headless/--headed"),
        assets_root: Path | None = typer.Option(
            None,
            "--assets-root",
            help="Assets root containing apps/ and plans/; fallback: CLI, MUNK_ASSETS_ROOT, <Munk AI home>/assets",
        ),
        max_steps: int | None = typer.Option(None, "--max-steps"),
        max_seconds: float | None = typer.Option(None, "--max-seconds"),
        interval: float | None = typer.Option(None, "--interval"),
        max_side: int | None = typer.Option(None, "--max-side"),
        icon_conf: float | None = typer.Option(None, "--icon-conf"),
        max_tokens: int | None = typer.Option(None, "--max-tokens"),
        temperature: float | None = typer.Option(None, "--temperature"),
        vl_max_side: int | None = typer.Option(None, "--vl-max-side"),
        config: Path | None = typer.Option(
            None,
            "--config",
            help="YAML config path; fallback: MUNK_CONFIG, <workspace>/.munk/config.yaml, <Munk AI profile home>/config/config.yaml",
        ),
        request_file: Path | None = typer.Option(None, "--request-file"),
        json_output: bool = typer.Option(False, "--json"),
        wait: bool = typer.Option(True, "--wait"),
        detach: bool = typer.Option(False, "--detach"),
    ) -> None:
        apply_workspace_home()
        boot_log("run case command invoked")
        from munk.adapters.cli.run_case_command import run_case_command

        command_kwargs: dict[str, Any] = {
            "app_id": app_id,
            "plan_id": plan_id,
            "case_id": case_id,
            "platform": platform,
            "device_ref": device_ref,
            "package": package,
            "bundle_id": bundle_id,
            "base_url": base_url,
            "origin": origin,
            "headless": headless,
            "assets_root": assets_root,
            "interval": interval,
            "max_side": max_side,
            "icon_conf": icon_conf,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "vl_max_side": vl_max_side,
            "config": config,
            "request_file": request_file,
            "json_output": json_output,
            "wait": wait,
            "detach": detach,
        }
        if max_steps is not None:
            command_kwargs["max_steps"] = max_steps
        if max_seconds is not None:
            command_kwargs["max_seconds"] = max_seconds
        run_case_command(**command_kwargs)

    @run_app.command("plan")
    def run_plan(
        app_id: str | None = typer.Option(None, "--app-id"),
        plan_id: str | None = typer.Option(None, "--plan-id"),
        platform: str | None = typer.Option(None, "--platform"),
        device_ref: str | None = typer.Option(None, "--device-ref", "--serial"),
        package: str | None = typer.Option(None, "--package"),
        bundle_id: str | None = typer.Option(None, "--bundle-id"),
        base_url: str | None = typer.Option(None, "--base-url"),
        origin: str | None = typer.Option(None, "--origin"),
        headless: bool = typer.Option(False, "--headless/--headed"),
        assets_root: Path | None = typer.Option(
            None,
            "--assets-root",
            help="Assets root containing apps/ and plans/; fallback: CLI, MUNK_ASSETS_ROOT, <Munk AI home>/assets",
        ),
        max_steps: int | None = typer.Option(None, "--max-steps"),
        max_seconds: float | None = typer.Option(None, "--max-seconds"),
        interval: float | None = typer.Option(None, "--interval"),
        max_side: int | None = typer.Option(None, "--max-side"),
        icon_conf: float | None = typer.Option(None, "--icon-conf"),
        max_tokens: int | None = typer.Option(None, "--max-tokens"),
        temperature: float | None = typer.Option(None, "--temperature"),
        vl_max_side: int | None = typer.Option(None, "--vl-max-side"),
        config: Path | None = typer.Option(
            None,
            "--config",
            help="YAML config path; fallback: MUNK_CONFIG, <workspace>/.munk/config.yaml, <Munk AI profile home>/config/config.yaml",
        ),
        fail_fast: bool = typer.Option(False, "--fail-fast"),
        request_file: Path | None = typer.Option(None, "--request-file"),
        json_output: bool = typer.Option(False, "--json"),
        wait: bool = typer.Option(True, "--wait"),
        detach: bool = typer.Option(False, "--detach"),
    ) -> None:
        apply_workspace_home()
        boot_log("run plan command invoked")
        from munk.adapters.cli.run_plan_command import run_plan_command

        command_kwargs: dict[str, Any] = {
            "app_id": app_id,
            "plan_id": plan_id,
            "platform": platform,
            "device_ref": device_ref,
            "package": package,
            "bundle_id": bundle_id,
            "base_url": base_url,
            "origin": origin,
            "headless": headless,
            "assets_root": assets_root,
            "interval": interval,
            "max_side": max_side,
            "icon_conf": icon_conf,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "vl_max_side": vl_max_side,
            "config": config,
            "fail_fast": fail_fast,
            "request_file": request_file,
            "json_output": json_output,
            "wait": wait,
            "detach": detach,
        }
        if max_steps is not None:
            command_kwargs["max_steps"] = max_steps
        if max_seconds is not None:
            command_kwargs["max_seconds"] = max_seconds
        run_plan_command(**command_kwargs)

    @run_app.command("plans", hidden=True)
    def run_plans(
        request_file: Path = typer.Option(..., "--request-file"),
        assets_root: Path | None = typer.Option(
            None,
            "--assets-root",
            help="Assets root containing apps/ and plans/; fallback: CLI, MUNK_ASSETS_ROOT, <Munk AI home>/assets",
        ),
        config: Path | None = typer.Option(
            None,
            "--config",
            help="YAML config path; fallback: MUNK_CONFIG, <workspace>/.munk/config.yaml, <Munk AI profile home>/config/config.yaml",
        ),
        json_output: bool = typer.Option(False, "--json"),
        wait: bool = typer.Option(True, "--wait"),
        detach: bool = typer.Option(False, "--detach"),
    ) -> None:
        apply_workspace_home()
        boot_log("run plans command invoked")
        from munk.adapters.cli.run_plans_command import run_plans_command

        run_plans_command(
            request_file=request_file,
            assets_root=assets_root,
            config=config,
            json_output=json_output,
            wait=wait,
            detach=detach,
        )

    @verify_app.command("change")
    def verify_change(
        app_id: str | None = typer.Option(None, "--app-id"),
        acceptance_criteria: list[str] | None = typer.Option(None, "--acceptance-criterion"),
        change_summary: str | None = typer.Option(None, "--change-summary"),
        changed_files: list[str] | None = typer.Option(None, "--changed-file"),
        review_orchestration: Path | None = typer.Option(None, "--review-orchestration"),
        requirement_doc: Path | None = typer.Option(None, "--requirement-doc"),
        technical_doc: Path | None = typer.Option(None, "--technical-doc"),
        device_ref: str | None = typer.Option(None, "--device-ref", "--serial"),
        package: str | None = typer.Option(None, "--package"),
        artifact_path: Path | None = typer.Option(None, "--artifact-path"),
        assets_root: Path | None = typer.Option(
            None,
            "--assets-root",
            help="Assets root containing apps/ and plans/; fallback: CLI, MUNK_ASSETS_ROOT, <Munk AI home>/assets",
        ),
        auto_run: bool = typer.Option(False, "--auto-run/--no-auto-run"),
        fail_fast: bool = typer.Option(False, "--fail-fast"),
        max_steps: int | None = typer.Option(None, "--max-steps"),
        max_seconds: float | None = typer.Option(None, "--max-seconds"),
        interval: float | None = typer.Option(None, "--interval"),
        max_side: int | None = typer.Option(None, "--max-side"),
        icon_conf: float | None = typer.Option(None, "--icon-conf"),
        max_tokens: int | None = typer.Option(None, "--max-tokens"),
        temperature: float | None = typer.Option(None, "--temperature"),
        vl_max_side: int | None = typer.Option(None, "--vl-max-side"),
        config: Path | None = typer.Option(
            None,
            "--config",
            help="YAML config path; fallback: MUNK_CONFIG, <workspace>/.munk/config.yaml, <Munk AI profile home>/config/config.yaml",
        ),
        request_file: Path | None = typer.Option(None, "--request-file"),
        json_output: bool = typer.Option(False, "--json"),
        wait: bool = typer.Option(True, "--wait"),
        detach: bool = typer.Option(False, "--detach"),
    ) -> None:
        apply_workspace_home()
        boot_log("verify change command invoked")
        from munk.adapters.cli.verify_change_command import verify_change_command

        verify_change_command(
            app_id=app_id,
            acceptance_criteria=acceptance_criteria,
            change_summary=change_summary,
            changed_files=changed_files,
            review_orchestration=review_orchestration,
            requirement_doc=requirement_doc,
            technical_doc=technical_doc,
            device_ref=device_ref,
            package=package,
            artifact_path=artifact_path,
            assets_root=assets_root,
            auto_run=auto_run,
            fail_fast=fail_fast,
            max_steps=max_steps,
            max_seconds=max_seconds,
            interval=interval,
            max_side=max_side,
            icon_conf=icon_conf,
            max_tokens=max_tokens,
            temperature=temperature,
            vl_max_side=vl_max_side,
            config=config,
            request_file=request_file,
            json_output=json_output,
            wait=wait,
            detach=detach,
        )
