import os
import sys
import time
from pathlib import Path

import typer

if getattr(sys, "frozen", False):
    os.environ.setdefault("PYDANTIC_DISABLE_PLUGINS", "__all__")

from munk.cli_command_groups import register_cli_command_groups
from munk.runtime_defaults import (
    DEFAULT_ICON_CONF,
    DEFAULT_MAX_SIDE,
)
from munk.storage_mode import StorageMode, apply_default_home
from munk.telemetry import build_telemetry_service
from munk.version import resolve_munk_version

app = typer.Typer(no_args_is_help=True)
run_app = typer.Typer(no_args_is_help=True)
verify_app = typer.Typer(no_args_is_help=True)
runs_app = typer.Typer(no_args_is_help=True)
mcp_app = typer.Typer(no_args_is_help=True)
data_app = typer.Typer(no_args_is_help=True)
apps_app = typer.Typer(no_args_is_help=True)
plans_app = typer.Typer(no_args_is_help=True)
cases_app = typer.Typer(no_args_is_help=True)
devices_app = typer.Typer(no_args_is_help=True)
app_lifecycle_app = typer.Typer(no_args_is_help=True)
app.add_typer(run_app, name="run")
app.add_typer(verify_app, name="verify")
app.add_typer(runs_app, name="runs")
app.add_typer(mcp_app, name="mcp")
app.add_typer(data_app, name="data")
app.add_typer(apps_app, name="apps")
app.add_typer(plans_app, name="plans")
app.add_typer(cases_app, name="cases")
app.add_typer(devices_app, name="devices")
app.add_typer(app_lifecycle_app, name="app")
_BOOT_START = time.perf_counter()


def _boot_log(message: str) -> None:
    if os.environ.get("MUNK_BOOT_LOG") != "1":
        return
    elapsed = time.perf_counter() - _BOOT_START
    sys.stderr.write(f"[boot +{elapsed:.3f}s] {message}\n")
    sys.stderr.flush()


def _apply_workspace_home() -> None:
    apply_default_home(StorageMode.WORKSPACE, workspace_root=Path.cwd())


@app.callback()
def app_callback() -> None:
    build_telemetry_service(workspace_root=Path.cwd()).capture_app_started(entrypoint="cli")


@app.command()
def plan(
    app_id: str | None = typer.Option(None, "--app-id"),
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
    artifact_url: str | None = typer.Option(None, "--artifact-url"),
    auto_run: bool = typer.Option(False, "--auto-run/--no-auto-run"),
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
    _apply_workspace_home()
    _boot_log("plan command invoked")
    from munk.adapters.cli.plan_command import plan_command

    plan_command(
        app_id=app_id,
        requirement_doc=requirement_doc,
        technical_doc=technical_doc,
        device_ref=device_ref,
        package=package,
        artifact_path=artifact_path,
        assets_root=assets_root,
        artifact_url=artifact_url,
        auto_run=auto_run,
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


@app.command()
def review(
    app_id: str | None = typer.Option(None, "--app-id"),
    change_summary: str | None = typer.Option(None, "--change-summary"),
    changed_files: list[str] | None = typer.Option(None, "--changed-file"),
    diff_text: str | None = typer.Option(None, "--diff-text"),
    requirement_doc: Path | None = typer.Option(None, "--requirement-doc"),
    technical_doc: Path | None = typer.Option(None, "--technical-doc"),
    review_query: str | None = typer.Option(None, "--review-query"),
    platform: list[str] | None = typer.Option(None, "--platform"),
    tag: list[str] | None = typer.Option(None, "--tag"),
    case_type: list[str] | None = typer.Option(None, "--case-type"),
    artifact_path: Path | None = typer.Option(None, "--artifact-path"),
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
    _apply_workspace_home()
    _boot_log("review command invoked")
    from munk.adapters.cli.review_command import review_command

    review_command(
        app_id=app_id,
        change_summary=change_summary,
        changed_files=changed_files,
        diff_text=diff_text,
        requirement_doc=requirement_doc,
        technical_doc=technical_doc,
        review_query=review_query,
        platform=platform,
        tag=tag,
        case_type=case_type,
        artifact_path=artifact_path,
        config=config,
        request_file=request_file,
        json_output=json_output,
        wait=wait,
        detach=detach,
    )


@app.command("knowledge-post-action", hidden=True)
def knowledge_post_action(
    request_file: Path = typer.Option(..., "--request-file"),
    config: Path | None = typer.Option(
        None,
        "--config",
        help="YAML config path; fallback: MUNK_CONFIG, <workspace>/.munk/config.yaml, <Munk AI profile home>/config/config.yaml",
    ),
    json_output: bool = typer.Option(False, "--json"),
    wait: bool = typer.Option(True, "--wait"),
    detach: bool = typer.Option(False, "--detach"),
) -> None:
    _apply_workspace_home()
    _boot_log("knowledge post action command invoked")
    from munk.adapters.cli.knowledge_post_action_command import knowledge_post_action_command

    knowledge_post_action_command(
        request_file=request_file,
        config=config,
        json_output=json_output,
        wait=wait,
        detach=detach,
    )


@app.command("optimize-case", hidden=True)
def optimize_case(
    request_file: Path = typer.Option(..., "--request-file"),
    config: Path | None = typer.Option(
        None,
        "--config",
        help="YAML config path; fallback: MUNK_CONFIG, <workspace>/.munk/config.yaml, <Munk AI profile home>/config/config.yaml",
    ),
    json_output: bool = typer.Option(False, "--json"),
    wait: bool = typer.Option(True, "--wait"),
    detach: bool = typer.Option(False, "--detach"),
) -> None:
    _apply_workspace_home()
    _boot_log("optimize case command invoked")
    from munk.adapters.cli.optimize_case_command import optimize_case_command

    optimize_case_command(
        request_file=request_file,
        config=config,
        json_output=json_output,
        wait=wait,
        detach=detach,
    )


@app.command()
def doctor() -> None:
    _boot_log("doctor command invoked")
    from munk.adapters.cli.doctor_command import doctor_command

    doctor_command()


@app.command()
def version() -> None:
    _boot_log("version command invoked")
    typer.echo(resolve_munk_version())


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(16888, "--port"),
    log_level: str = typer.Option("info", "--log-level"),
    disable_mcp: bool = typer.Option(False, "--disable-mcp"),
    kill_port_conflicts: bool = typer.Option(
        False,
        "--kill-port-conflicts",
        help="Kill listening processes already occupying the requested port before starting serve.",
    ),
) -> None:
    _boot_log("serve command invoked")
    from munk.adapters.cli.serve_command import serve_command

    serve_command(
        host=host,
        port=port,
        log_level=log_level,
        disable_mcp=disable_mcp,
        kill_port_conflicts=kill_port_conflicts,
    )


@app.command()
def capture() -> None:
    _boot_log("capture command invoked")
    from munk.adapters.cli.capture_command import capture_command

    capture_command()


@app.command()
def annotate(
    image: Path = typer.Argument(..., exists=True, readable=True),
    output: Path | None = typer.Option(None, "--output", "-o"),
    max_side: int = typer.Option(DEFAULT_MAX_SIDE, "--max-side"),
    icon_conf: float = typer.Option(DEFAULT_ICON_CONF, "--icon-conf"),
) -> None:
    _boot_log("annotate command invoked")
    from munk.adapters.cli.annotate_command import annotate_command

    annotate_command(image, output, max_side, icon_conf)

register_cli_command_groups(
    app_lifecycle_app=app_lifecycle_app,
    run_app=run_app,
    verify_app=verify_app,
    runs_app=runs_app,
    mcp_app=mcp_app,
    data_app=data_app,
    apps_app=apps_app,
    plans_app=plans_app,
    cases_app=cases_app,
    devices_app=devices_app,
    apply_workspace_home=_apply_workspace_home,
    boot_log=_boot_log,
)


def main() -> None:
    _boot_log("cli main")
    app()


if __name__ == "__main__":
    main()
