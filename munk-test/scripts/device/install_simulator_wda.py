#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from install_wda_shared import (  # noqa: E402
    DEFAULT_WDA_URL,
    DEFAULT_WDA_VERSION,
    CommandRunner,
    Downloader,
    InstallWDAError,
    InstallWDAResult,
    SleepFn,
    StatusChecker,
    default_command_runner,
    prepare_dependencies,
    print_result,
    run_json_command,
    wait_for_healthy,
)

DEFAULT_WDA_BUNDLE_ID = "com.facebook.WebDriverAgentRunner.xctrunner"


@dataclass(frozen=True)
class InstallSimulatorWDAOptions:
    simulator_udid: str
    wda_version: str = DEFAULT_WDA_VERSION
    source_dir: Path | None = None
    force_download: bool = False
    force_rebuild: bool = False
    wda_url: str = DEFAULT_WDA_URL


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download, build, install and launch WebDriverAgent for an iOS Simulator.")
    parser.add_argument("--simulator-udid", required=True, help="Booted iOS Simulator UDID.")
    parser.add_argument("--wda-version", default=DEFAULT_WDA_VERSION, help=f"WDA git tag to download. Default: {DEFAULT_WDA_VERSION}")
    parser.add_argument("--source-dir", type=Path, default=None, help="Use an existing WDA source directory instead of downloading.")
    parser.add_argument("--force-download", action="store_true", help="Re-download and re-extract WDA sources.")
    parser.add_argument("--force-rebuild", action="store_true", help="Rebuild WDA even if a previous build output exists.")
    parser.add_argument("--wda-url", default=DEFAULT_WDA_URL, help=f"WDA healthcheck URL. Default: {DEFAULT_WDA_URL}")
    return parser


def parse_args(argv: list[str] | None = None) -> InstallSimulatorWDAOptions:
    args = build_parser().parse_args(argv)
    return InstallSimulatorWDAOptions(
        simulator_udid=args.simulator_udid,
        wda_version=args.wda_version,
        source_dir=args.source_dir,
        force_download=bool(args.force_download),
        force_rebuild=bool(args.force_rebuild),
        wda_url=args.wda_url,
    )


def main(argv: list[str] | None = None) -> int:
    options = parse_args(argv)
    try:
        result = install_simulator_wda(options)
    except InstallWDAError as exc:
        result = InstallWDAResult(
            ok=False,
            stage=exc.stage,
            target_kind="simulator",
            wda_version=options.wda_version,
            simulator_udid=options.simulator_udid,
            wda_url=options.wda_url,
            message=exc.message,
        )
        print_result(result)
        return 1

    print_result(result)
    return 0


def install_simulator_wda(
    options: InstallSimulatorWDAOptions,
    *,
    command_runner: CommandRunner | None = None,
    downloader: Downloader | None = None,
    status_checker: StatusChecker | None = None,
    sleep_fn: SleepFn | None = None,
) -> InstallWDAResult:
    run = command_runner or default_command_runner
    source_dir = prepare_dependencies(
        wda_version=options.wda_version,
        source_dir=options.source_dir,
        force_download=options.force_download,
        command_runner=run,
        downloader=downloader,
    )
    _ensure_simctl_available(run)
    _ensure_simulator_booted(options.simulator_udid, run)
    app_path, derived_data_path = _build_wda_for_simulator(
        source_dir=source_dir,
        options=options,
        command_runner=run,
    )
    _install_wda_app(options.simulator_udid, app_path, run)
    _launch_wda_runner(options.simulator_udid, run)
    wait_for_healthy(options.wda_url, status_checker=status_checker, sleep_fn=sleep_fn)
    return InstallWDAResult(
        ok=True,
        stage="completed",
        target_kind="simulator",
        wda_version=options.wda_version,
        source_dir=str(source_dir),
        simulator_udid=options.simulator_udid,
        wda_url=options.wda_url,
        app_path=str(app_path),
        derived_data_path=str(derived_data_path),
        message="WebDriverAgent is installed and healthy on the selected iOS Simulator.",
    )


def _ensure_simctl_available(command_runner: CommandRunner) -> None:
    try:
        command_runner(["xcrun", "simctl", "help"], False)
    except Exception as exc:  # noqa: BLE001
        raise InstallWDAError("environment_check_failed", f"required simulator tooling is unavailable: {exc}") from exc


def _ensure_simulator_booted(simulator_udid: str, command_runner: CommandRunner) -> None:
    try:
        payload = run_json_command(["xcrun", "simctl", "list", "devices", "--json"], command_runner)
    except Exception as exc:  # noqa: BLE001
        raise InstallWDAError("environment_check_failed", f"failed to query iOS simulators: {exc}") from exc
    devices_obj = payload.get("devices")
    if not isinstance(devices_obj, dict):
        raise InstallWDAError("environment_check_failed", "simctl device list returned an unexpected JSON payload")
    devices = cast(dict[str, Any], devices_obj)
    for entries in devices.values():
        if not isinstance(entries, list):
            continue
        for entry in cast(list[dict[str, Any]], entries):
            if not isinstance(entry, dict):
                continue
            if entry.get("udid") != simulator_udid:
                continue
            if str(entry.get("state", "")).lower() != "booted":
                raise InstallWDAError("environment_check_failed", f"selected simulator is not booted: {simulator_udid}")
            return
    raise InstallWDAError("environment_check_failed", f"selected simulator was not found: {simulator_udid}")


def _build_wda_for_simulator(
    *,
    source_dir: Path,
    options: InstallSimulatorWDAOptions,
    command_runner: CommandRunner,
) -> tuple[Path, Path]:
    derived_data_path = source_dir.parent / "derived-data-simulator"
    app_path = derived_data_path / "Build" / "Products" / "Debug-iphonesimulator" / "WebDriverAgentRunner-Runner.app"
    if options.force_rebuild and derived_data_path.exists():
        shutil.rmtree(derived_data_path)
    if app_path.exists() and not options.force_rebuild:
        return app_path, derived_data_path

    project_path = source_dir / "WebDriverAgent.xcodeproj"
    if not project_path.exists():
        raise InstallWDAError("build_failed", f"WDA project file is missing: {project_path}")

    build_command = [
        "xcodebuild",
        "-project",
        str(project_path),
        "-scheme",
        "WebDriverAgentRunner",
        "-sdk",
        "iphonesimulator",
        "-destination",
        f"id={options.simulator_udid}",
        "-derivedDataPath",
        str(derived_data_path),
        "build-for-testing",
    ]
    try:
        command_runner(build_command, False)
    except Exception as exc:  # noqa: BLE001
        raise InstallWDAError("build_failed", f"failed to build WebDriverAgentRunner: {exc}") from exc
    if not app_path.exists():
        raise InstallWDAError("build_failed", f"expected build output is missing: {app_path}")
    return app_path, derived_data_path


def _install_wda_app(simulator_udid: str, app_path: Path, command_runner: CommandRunner) -> None:
    try:
        command_runner(["xcrun", "simctl", "install", simulator_udid, str(app_path)], False)
    except Exception as exc:  # noqa: BLE001
        raise InstallWDAError("install_failed", f"failed to install WDA on simulator: {exc}") from exc


def _launch_wda_runner(simulator_udid: str, command_runner: CommandRunner) -> None:
    try:
        command_runner(["xcrun", "simctl", "launch", simulator_udid, DEFAULT_WDA_BUNDLE_ID], False)
    except Exception as exc:  # noqa: BLE001
        raise InstallWDAError("launch_failed", f"failed to launch WDA on simulator: {exc}") from exc
if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
