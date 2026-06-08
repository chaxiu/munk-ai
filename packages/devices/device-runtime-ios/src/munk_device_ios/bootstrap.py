from __future__ import annotations

import subprocess
import time
from typing import Callable

import httpx
from munk.app import AppTarget

from .discovery import CommandRunner, ResolvedIOSDeviceTarget

StatusChecker = Callable[[str], bool]
SleepFn = Callable[[float], None]

DEFAULT_WDA_BUNDLE_ID = "com.facebook.WebDriverAgentRunner.xctrunner"
DEFAULT_WDA_URL = "http://127.0.0.1:8100"


def ensure_simulator_wda_ready(
    *,
    target: ResolvedIOSDeviceTarget,
    app_target: AppTarget,
    command_runner: CommandRunner | None = None,
    status_checker: StatusChecker | None = None,
    sleep_fn: SleepFn | None = None,
) -> str:
    if target.kind != "simulator":
        raise NotImplementedError("real device execution is deferred to MP4 Phase 3")
    if target.is_booted is False:
        raise RuntimeError(f"selected iOS simulator is not booted: {target.device_ref}")

    resolved_wda_url = _resolve_wda_url(app_target)
    probe = status_checker or _default_status_checker
    if probe(resolved_wda_url):
        return resolved_wda_url

    launch_bundle_id = app_target.launch_context.get("wda_bundle_id", DEFAULT_WDA_BUNDLE_ID)
    _launch_simulator_wda(
        target=target,
        bundle_id=launch_bundle_id,
        command_runner=command_runner,
    )

    timeout_sec = float(app_target.launch_context.get("wda_bootstrap_timeout_sec", "15"))
    interval_sec = float(app_target.launch_context.get("wda_bootstrap_poll_interval_sec", "1"))
    deadline = time.monotonic() + timeout_sec
    sleeper = sleep_fn or time.sleep
    while time.monotonic() < deadline:
        if probe(resolved_wda_url):
            return resolved_wda_url
        sleeper(interval_sec)

    raise RuntimeError(
        "iOS simulator WDA is not reachable; run `python3 scripts/device/install_simulator_wda.py --simulator-udid <udid>` first and ensure WebDriverAgentRunner is healthy on the selected simulator"
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
    subprocess.run(command, check=True, capture_output=True, text=True)


def _default_status_checker(base_url: str) -> bool:
    try:
        response = httpx.get(f"{base_url.rstrip('/')}/status", timeout=2.0)
    except httpx.HTTPError:
        return False
    return response.status_code == 200
