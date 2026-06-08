import os
import sys
import time
from pathlib import Path
from typing import Any

import typer

if getattr(sys, "frozen", False):
    os.environ.setdefault("PYDANTIC_DISABLE_PLUGINS", "__all__")

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
    _apply_workspace_home()
    _boot_log("app launch command invoked")
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
    _apply_workspace_home()
    _boot_log("app stop command invoked")
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
    _apply_workspace_home()
    _boot_log("app install command invoked")
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
    _apply_workspace_home()
    _boot_log("run case command invoked")
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
    run_case_command(
        **command_kwargs,
    )


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
    _apply_workspace_home()
    _boot_log("run plan command invoked")
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
    run_plan_command(
        **command_kwargs,
    )


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
    _apply_workspace_home()
    _boot_log("run plans command invoked")
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
    change_summary: str | None = typer.Option(None, "--change-summary"),
    changed_files: list[str] | None = typer.Option(None, "--changed-file"),
    review_orchestration: Path | None = typer.Option(None, "--review-orchestration"),
    requirement_doc: Path | None = typer.Option(None, "--requirement-doc"),
    technical_doc: Path | None = typer.Option(None, "--technical-doc"),
    previous_report: Path | None = typer.Option(None, "--previous-report"),
    device_ref: str | None = typer.Option(None, "--device-ref", "--serial"),
    package: str | None = typer.Option(None, "--package"),
    artifact_path: Path | None = typer.Option(None, "--artifact-path"),
    assets_root: Path | None = typer.Option(
        None,
        "--assets-root",
        help="Assets root containing apps/ and plans/; fallback: CLI, MUNK_ASSETS_ROOT, <Munk AI home>/assets",
    ),
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
    _boot_log("verify change command invoked")
    from munk.adapters.cli.verify_change_command import verify_change_command

    verify_change_command(
        app_id=app_id,
        change_summary=change_summary,
        changed_files=changed_files,
        review_orchestration=review_orchestration,
        requirement_doc=requirement_doc,
        technical_doc=technical_doc,
        previous_report=previous_report,
        device_ref=device_ref,
        package=package,
        artifact_path=artifact_path,
        assets_root=assets_root,
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


@runs_app.command("get")
def runs_get(
    operation_id: str = typer.Option(..., "--operation-id"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    _apply_workspace_home()
    _boot_log("runs get command invoked")
    from munk.adapters.cli.runs_get_command import runs_get_command

    runs_get_command(operation_id=operation_id, json_output=json_output)


@runs_app.command("events")
def runs_events(
    operation_id: str = typer.Option(..., "--operation-id"),
    after_seq: int = typer.Option(0, "--after-seq"),
    limit: int = typer.Option(100, "--limit"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    _apply_workspace_home()
    _boot_log("runs events command invoked")
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
    _apply_workspace_home()
    _boot_log("runs artifacts command invoked")
    from munk.adapters.cli.runs_artifacts_command import runs_artifacts_command

    runs_artifacts_command(operation_id=operation_id, json_output=json_output)


@runs_app.command("cancel")
def runs_cancel(
    operation_id: str = typer.Option(..., "--operation-id"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    _apply_workspace_home()
    _boot_log("runs cancel command invoked")
    from munk.adapters.cli.runs_cancel_command import runs_cancel_command

    runs_cancel_command(operation_id=operation_id, json_output=json_output)


@runs_app.command("reproduce")
def runs_reproduce(
    operation_id: str = typer.Option(..., "--operation-id"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    _apply_workspace_home()
    _boot_log("runs reproduce command invoked")
    from munk.adapters.cli.runs_reproduce_command import runs_reproduce_command

    runs_reproduce_command(operation_id=operation_id, json_output=json_output)


@runs_app.command("cleanup-locks")
def runs_cleanup_locks(
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    _apply_workspace_home()
    _boot_log("runs cleanup-locks command invoked")
    from munk.adapters.cli.runs_cleanup_locks_command import runs_cleanup_locks_command

    runs_cleanup_locks_command(json_output=json_output)


@mcp_app.command("serve")
def mcp_serve(
) -> None:
    _boot_log("mcp serve command invoked")
    from munk.adapters.cli.mcp_command import mcp_command

    mcp_command()


@data_app.command("home")
def data_home(
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    _apply_workspace_home()
    _boot_log("data home command invoked")
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
    _apply_workspace_home()
    _boot_log("data search-cases command invoked")
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
    _apply_workspace_home()
    _boot_log("data rebuild-case-index command invoked")
    from munk.adapters.cli.data_rebuild_case_index_command import data_rebuild_case_index_command

    data_rebuild_case_index_command(json_output=json_output)


@apps_app.command("list")
def apps_list(
    platform: str | None = typer.Option(None, "--platform"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    _apply_workspace_home()
    _boot_log("apps list command invoked")
    from munk.adapters.cli.apps_list_command import apps_list_command

    apps_list_command(platform=platform, json_output=json_output)


@apps_app.command("get")
def apps_get(
    app_id: str = typer.Option(..., "--app-id"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    _apply_workspace_home()
    _boot_log("apps get command invoked")
    from munk.adapters.cli.apps_get_command import apps_get_command

    apps_get_command(app_id=app_id, json_output=json_output)


@apps_app.command("create")
def apps_create(
    request_file: Path = typer.Option(..., "--request-file"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    _apply_workspace_home()
    _boot_log("apps create command invoked")
    from munk.adapters.cli.apps_create_command import apps_create_command

    apps_create_command(request_file=request_file, json_output=json_output)


@apps_app.command("update")
def apps_update(
    app_id: str = typer.Option(..., "--app-id"),
    request_file: Path = typer.Option(..., "--request-file"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    _apply_workspace_home()
    _boot_log("apps update command invoked")
    from munk.adapters.cli.apps_update_command import apps_update_command

    apps_update_command(app_id=app_id, request_file=request_file, json_output=json_output)


@apps_app.command("delete")
def apps_delete(
    app_id: str = typer.Option(..., "--app-id"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    _apply_workspace_home()
    _boot_log("apps delete command invoked")
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
    _apply_workspace_home()
    _boot_log("apps candidates-list command invoked")
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
    _apply_workspace_home()
    _boot_log("apps candidates-approve command invoked")
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
    _apply_workspace_home()
    _boot_log("apps candidates-reject command invoked")
    from munk.adapters.cli.knowledge_candidates_reject_command import knowledge_candidates_reject_command

    knowledge_candidates_reject_command(
        app_id=app_id,
        candidate_id=candidate_id,
        reviewed_by=reviewed_by,
        review_note=review_note,
        json_output=json_output,
    )


@plans_app.command("list")
def plans_list(
    app_id: str | None = typer.Option(None, "--app-id"),
    source: str | None = typer.Option(None, "--source"),
    limit: int = typer.Option(20, "--limit", min=1, max=200),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    _apply_workspace_home()
    _boot_log("plans list command invoked")
    from munk.adapters.cli.plans_list_command import plans_list_command

    plans_list_command(app_id=app_id, source=source, limit=limit, json_output=json_output)


@plans_app.command("get")
def plans_get(
    app_id: str = typer.Option(..., "--app-id"),
    plan_id: str = typer.Option(..., "--plan-id"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    _apply_workspace_home()
    _boot_log("plans get command invoked")
    from munk.adapters.cli.plans_get_command import plans_get_command

    plans_get_command(app_id=app_id, plan_id=plan_id, json_output=json_output)


@plans_app.command("reorder-cases")
def plans_reorder_cases(
    app_id: str = typer.Option(..., "--app-id"),
    plan_id: str = typer.Option(..., "--plan-id"),
    request_file: Path = typer.Option(..., "--request-file"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    _apply_workspace_home()
    _boot_log("plans reorder-cases command invoked")
    from munk.adapters.cli.plans_reorder_cases_command import plans_reorder_cases_command

    plans_reorder_cases_command(app_id=app_id, plan_id=plan_id, request_file=request_file, json_output=json_output)


@cases_app.command("get")
def cases_get(
    app_id: str = typer.Option(..., "--app-id"),
    plan_id: str = typer.Option(..., "--plan-id"),
    case_id: str = typer.Option(..., "--case-id"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    _apply_workspace_home()
    _boot_log("cases get command invoked")
    from munk.adapters.cli.cases_get_command import cases_get_command

    cases_get_command(app_id=app_id, plan_id=plan_id, case_id=case_id, json_output=json_output)


@cases_app.command("add")
def cases_add(
    app_id: str = typer.Option(..., "--app-id"),
    plan_id: str = typer.Option(..., "--plan-id"),
    request_file: Path = typer.Option(..., "--request-file"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    _apply_workspace_home()
    _boot_log("cases add command invoked")
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
    _apply_workspace_home()
    _boot_log("cases replace command invoked")
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
    _apply_workspace_home()
    _boot_log("cases delete command invoked")
    from munk.adapters.cli.cases_delete_command import cases_delete_command

    cases_delete_command(app_id=app_id, plan_id=plan_id, case_id=case_id, json_output=json_output)


@devices_app.command("list")
def devices_list(
    platform: str | None = typer.Option(None, "--platform"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    _apply_workspace_home()
    _boot_log("devices list command invoked")
    from munk.adapters.cli.devices_list_command import devices_list_command

    devices_list_command(platform=platform, json_output=json_output)


def main() -> None:
    _boot_log("cli main")
    app()


if __name__ == "__main__":
    main()
