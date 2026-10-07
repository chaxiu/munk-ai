from __future__ import annotations

from pathlib import Path
from typing import Callable

import typer


def register_cli_app_lifecycle_commands(
    *,
    app_lifecycle_app: typer.Typer,
    apply_workspace_home: Callable[[], None],
    boot_log: Callable[[str], None],
) -> None:
    @app_lifecycle_app.command("launch")
    def app_launch(
        app_id: str | None = typer.Option(None, "--app-id"),
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
        request_file: Path | None = typer.Option(None, "--request-file"),
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        apply_workspace_home()
        boot_log("app launch command invoked")
        from munk.adapters.cli.app_launch_command import app_launch_command

        app_launch_command(
            app_id=app_id,
            platform=platform,
            device_ref=device_ref,
            package=package,
            bundle_id=bundle_id,
            base_url=base_url,
            origin=origin,
            headless=headless,
            assets_root=assets_root,
            request_file=request_file,
            json_output=json_output,
        )

    @app_lifecycle_app.command("stop")
    def app_stop(
        app_id: str | None = typer.Option(None, "--app-id"),
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
        request_file: Path | None = typer.Option(None, "--request-file"),
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        apply_workspace_home()
        boot_log("app stop command invoked")
        from munk.adapters.cli.app_stop_command import app_stop_command

        app_stop_command(
            app_id=app_id,
            platform=platform,
            device_ref=device_ref,
            package=package,
            bundle_id=bundle_id,
            base_url=base_url,
            origin=origin,
            headless=headless,
            assets_root=assets_root,
            request_file=request_file,
            json_output=json_output,
        )

    @app_lifecycle_app.command("install")
    def app_install(
        app_id: str | None = typer.Option(None, "--app-id"),
        artifact_path: Path | None = typer.Option(None, "--artifact-path"),
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
        request_file: Path | None = typer.Option(None, "--request-file"),
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        apply_workspace_home()
        boot_log("app install command invoked")
        from munk.adapters.cli.app_install_command import app_install_command

        app_install_command(
            app_id=app_id,
            artifact_path=artifact_path,
            platform=platform,
            device_ref=device_ref,
            package=package,
            bundle_id=bundle_id,
            base_url=base_url,
            origin=origin,
            headless=headless,
            assets_root=assets_root,
            request_file=request_file,
            json_output=json_output,
        )
