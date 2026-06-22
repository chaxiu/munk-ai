from __future__ import annotations

from dataclasses import dataclass
import subprocess
import time
from typing import Callable, cast

import httpx
from munk.app import AppTarget
from munk.services.ios import IOSDeviceBridgeDiagnosticsContext, get_default_ios_device_bridge_manager

from .discovery import CommandRunner, ResolvedIOSDeviceTarget

StatusChecker = Callable[[str], bool]
SleepFn = Callable[[float], None]

DEFAULT_WDA_BUNDLE_ID = "sh.munk.wda.xctrunner"
DEFAULT_WDA_URL = "http://127.0.0.1:8100"


@dataclass(frozen=True)
class IOSWDAReadyResult:
    wda_url: str | None = None
    provider_kind: str = "http"
    bridge_base_url: str | None = None
    bridge_session_id: str | None = None
    bridge_backend_kind: str | None = None


def ensure_ios_wda_ready(
    *,
    target: ResolvedIOSDeviceTarget,
    app_target: AppTarget,
    command_runner: CommandRunner | None = None,
    status_checker: StatusChecker | None = None,
    sleep_fn: SleepFn | None = None,
    diagnostics_context: IOSDeviceBridgeDiagnosticsContext | None = None,
) -> IOSWDAReadyResult:
    if target.kind == "simulator":
        return _ensure_simulator_wda_ready(
            target=target,
            app_target=app_target,
            command_runner=command_runner,
            status_checker=status_checker,
            sleep_fn=sleep_fn,
        )
    if target.kind == "real_device":
        return _ensure_real_device_wda_ready(
            target=target,
            app_target=app_target,
            command_runner=command_runner,
            status_checker=status_checker,
            sleep_fn=sleep_fn,
            diagnostics_context=diagnostics_context,
        )
    raise RuntimeError(f"unsupported iOS device target kind: {target.kind}")


def ensure_simulator_wda_ready(
    *,
    target: ResolvedIOSDeviceTarget,
    app_target: AppTarget,
    command_runner: CommandRunner | None = None,
    status_checker: StatusChecker | None = None,
    sleep_fn: SleepFn | None = None,
) -> str:
    result = _ensure_simulator_wda_ready(
        target=target,
        app_target=app_target,
        command_runner=command_runner,
        status_checker=status_checker,
        sleep_fn=sleep_fn,
    )
    if result.wda_url is None:
        raise RuntimeError("simulator bootstrap did not produce a wda_url")
    return result.wda_url


def _ensure_simulator_wda_ready(
    *,
    target: ResolvedIOSDeviceTarget,
    app_target: AppTarget,
    command_runner: CommandRunner | None,
    status_checker: StatusChecker | None,
    sleep_fn: SleepFn | None,
) -> IOSWDAReadyResult:
    if target.is_booted is False:
        raise RuntimeError(f"selected iOS simulator is not booted: {target.device_ref}")

    resolved_wda_url = _resolve_wda_url(app_target)
    probe = status_checker or _default_status_checker
    if probe(resolved_wda_url):
        return IOSWDAReadyResult(wda_url=resolved_wda_url)

    launch_bundle_id = app_target.launch_context.get("wda_bundle_id", DEFAULT_WDA_BUNDLE_ID)
    _launch_simulator_wda(
        target=target,
        bundle_id=launch_bundle_id,
        command_runner=command_runner,
    )

    _wait_for_healthy_wda(
        resolved_wda_url,
        app_target=app_target,
        status_checker=probe,
        sleep_fn=sleep_fn,
    )
    return IOSWDAReadyResult(wda_url=resolved_wda_url)


def _ensure_real_device_wda_ready(
    *,
    target: ResolvedIOSDeviceTarget,
    app_target: AppTarget,
    command_runner: CommandRunner | None,
    status_checker: StatusChecker | None,
    sleep_fn: SleepFn | None,
    diagnostics_context: IOSDeviceBridgeDiagnosticsContext | None = None,
) -> IOSWDAReadyResult:
    if target.udid is None:
        raise RuntimeError("resolved iOS real-device target is missing udid")

    configured_wda_url = app_target.launch_context.get("wda_url")
    probe = status_checker or _default_status_checker
    if configured_wda_url:
        if probe(configured_wda_url):
            return IOSWDAReadyResult(wda_url=configured_wda_url, provider_kind="http")
        _launch_real_device_wda(
            target=target,
            bundle_id=app_target.launch_context.get("wda_bundle_id", DEFAULT_WDA_BUNDLE_ID),
            command_runner=command_runner,
        )
        _wait_for_healthy_wda(
            configured_wda_url,
            app_target=app_target,
            status_checker=probe,
            sleep_fn=sleep_fn,
            failure_message=(
                "iOS real-device WDA is not reachable at the configured wda_url; ensure the device already has "
                "WebDriverAgentRunner installed, the provided route is valid, and the runner can be launched"
            ),
        )
        return IOSWDAReadyResult(wda_url=configured_wda_url, provider_kind="http")

    manager = get_default_ios_device_bridge_manager()
    if app_target.ios is None:
        raise RuntimeError("ios runtime requires an ios app_target")
    session = manager.create_session(
        device_udid=target.udid,
        bundle_id=app_target.ios.bundle_id,
        wda_bundle_id=app_target.launch_context.get("wda_bundle_id", DEFAULT_WDA_BUNDLE_ID),
        platform_version=cast(str | None, target.raw.get("platform_version") or target.raw.get("os_version")),
        diagnostics=diagnostics_context,
    )
    return IOSWDAReadyResult(
        provider_kind="bridge",
        bridge_base_url=session.base_url,
        bridge_session_id=session.session_id,
        bridge_backend_kind=session.backend_kind,
    )


def _resolve_wda_url(app_target: AppTarget) -> str:
    configured = app_target.launch_context.get("wda_url")
    if configured:
        return configured
    return DEFAULT_WDA_URL


def _launch_simulator_wda(
    *,
    target: ResolvedIOSDeviceTarget,
    bundle_id: str,
    command_runner: CommandRunner | None,
) -> None:
    if target.udid is None:
        raise RuntimeError("resolved iOS simulator target is missing udid")
    command: list[str] = ["xcrun", "simctl", "launch", target.udid, bundle_id]
    if command_runner is not None:
        command_runner(command)
        return
    _run_checked_command(command, context="failed to launch iOS simulator WebDriverAgentRunner")


def _launch_real_device_wda(
    *,
    target: ResolvedIOSDeviceTarget,
    bundle_id: str,
    command_runner: CommandRunner | None,
) -> None:
    if target.udid is None:
        raise RuntimeError("resolved iOS real-device target is missing udid")
    command: list[str] = ["xcrun", "devicectl", "device", "process", "launch", "--device", target.udid, bundle_id]
    if command_runner is not None:
        command_runner(command)
        return
    _run_checked_command(command, context="failed to launch iOS real-device WebDriverAgentRunner")


def _wait_for_healthy_wda(
    wda_url: str,
    *,
    app_target: AppTarget,
    status_checker: StatusChecker,
    sleep_fn: SleepFn | None,
    failure_message: str | None = None,
) -> None:
    timeout_sec = float(app_target.launch_context.get("wda_bootstrap_timeout_sec", "15"))
    interval_sec = float(app_target.launch_context.get("wda_bootstrap_poll_interval_sec", "1"))
    deadline = time.monotonic() + timeout_sec
    sleeper = sleep_fn or time.sleep
    while time.monotonic() < deadline:
        if status_checker(wda_url):
            return
        sleeper(interval_sec)
    raise RuntimeError(
        failure_message
        or (
            "iOS simulator WDA is not reachable; run `python3 scripts/device/install_simulator_wda.py "
            "--simulator-udid <udid>` first and ensure WebDriverAgentRunner is healthy on the selected simulator"
        )
    )


def _default_status_checker(base_url: str) -> bool:
    try:
        response = httpx.get(f"{base_url.rstrip('/')}/status", timeout=2.0)
    except httpx.HTTPError:
        return False
    return response.status_code == 200
def _run_checked_command(command: list[str], *, context: str) -> None:
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        details: list[str] = [context, f"command={' '.join(command)}", f"exit_code={exc.returncode}"]
        if exc.stdout:
            details.append(f"stdout={exc.stdout.strip()}")
        if exc.stderr:
            details.append(f"stderr={exc.stderr.strip()}")
        raise RuntimeError("; ".join(details)) from exc
