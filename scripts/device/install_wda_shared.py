from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, cast

DEFAULT_WDA_VERSION = "v12.2.2"
DEFAULT_WDA_REPO = "appium/WebDriverAgent"
DEFAULT_WDA_URL = "http://127.0.0.1:8100"
DEFAULT_HEALTHCHECK_TIMEOUT_SEC = 20.0
DEFAULT_HEALTHCHECK_INTERVAL_SEC = 1.0

ROOT_DIR = Path(__file__).resolve().parents[1]

CommandRunner = Callable[[list[str], bool], str | None]
Downloader = Callable[[str, Path], None]
SleepFn = Callable[[float], None]
StatusChecker = Callable[[str], bool]


@dataclass(frozen=True)
class InstallWDAResult:
    ok: bool
    stage: str
    target_kind: str
    wda_version: str
    source_dir: str | None = None
    simulator_udid: str | None = None
    device_udid: str | None = None
    wda_url: str | None = None
    local_wda_url: str | None = None
    app_path: str | None = None
    derived_data_path: str | None = None
    iproxy_pid: int | None = None
    signing_env_file: str | None = None
    message: str | None = None


class InstallWDAError(RuntimeError):
    def __init__(self, stage: str, message: str) -> None:
        super().__init__(message)
        self.stage = stage
        self.message = message


def print_result(payload: InstallWDAResult) -> None:
    print(json.dumps(asdict(payload), ensure_ascii=False, indent=2))


def prepare_dependencies(
    *,
    wda_version: str,
    source_dir: Path | None,
    force_download: bool,
    command_runner: CommandRunner | None = None,
    downloader: Downloader | None = None,
) -> Path:
    run = command_runner or default_command_runner
    download = downloader or default_downloader
    ensure_apple_tooling(run)
    return prepare_source_dir(
        wda_version=wda_version,
        source_dir=source_dir,
        force_download=force_download,
        downloader=download,
    )


def ensure_apple_tooling(command_runner: CommandRunner) -> None:
    try:
        command_runner(["xcodebuild", "-version"], False)
    except Exception as exc:  # noqa: BLE001
        raise InstallWDAError("environment_check_failed", f"required Apple tooling is unavailable: {exc}") from exc


def prepare_source_dir(
    *,
    wda_version: str,
    source_dir: Path | None,
    force_download: bool,
    downloader: Downloader,
) -> Path:
    if source_dir is not None:
        resolved = source_dir.expanduser().resolve()
        if not resolved.exists():
            raise InstallWDAError("download_failed", f"provided source_dir does not exist: {resolved}")
        return resolved

    cache_root = default_cache_root() / wda_version
    resolved_source_dir = cache_root / "source"
    archive_path = cache_root / f"WebDriverAgent-{wda_version}.tar.gz"
    if force_download and cache_root.exists():
        shutil.rmtree(cache_root)
    cache_root.mkdir(parents=True, exist_ok=True)

    if not resolved_source_dir.exists():
        archive_url = build_archive_url(wda_version)
        try:
            downloader(archive_url, archive_path)
        except Exception as exc:  # noqa: BLE001
            raise InstallWDAError("download_failed", f"failed to download WDA source archive: {exc}") from exc
        try:
            extract_archive(archive_path, resolved_source_dir)
        except Exception as exc:  # noqa: BLE001
            raise InstallWDAError("extract_failed", f"failed to extract WDA source archive: {exc}") from exc
    return resolved_source_dir


def wait_for_healthy(
    wda_url: str,
    *,
    status_checker: StatusChecker | None = None,
    sleep_fn: SleepFn | None = None,
    timeout_sec: float = DEFAULT_HEALTHCHECK_TIMEOUT_SEC,
    interval_sec: float = DEFAULT_HEALTHCHECK_INTERVAL_SEC,
) -> None:
    probe = status_checker or default_status_checker
    sleeper = sleep_fn or time.sleep
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if probe(wda_url):
            return
        sleeper(interval_sec)
    raise InstallWDAError("healthcheck_failed", f"WDA did not become healthy at {wda_url}")


def build_archive_url(wda_version: str) -> str:
    return f"https://github.com/{DEFAULT_WDA_REPO}/archive/refs/tags/{wda_version}.tar.gz"


def default_cache_root() -> Path:
    munk_home = os.environ.get("MUNK_HOME")
    if munk_home:
        return Path(munk_home).expanduser().resolve() / "cache" / "ios" / "wda"
    return ROOT_DIR / ".munk" / "cache" / "ios" / "wda"


def extract_archive(archive_path: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_extract_dir = destination.parent / f"{destination.name}-tmp"
    if temp_extract_dir.exists():
        shutil.rmtree(temp_extract_dir)
    temp_extract_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "r:gz") as tar:
        if sys.version_info >= (3, 12):
            tar.extractall(temp_extract_dir, filter="data")
        else:
            tar.extractall(temp_extract_dir)

    extracted_roots = [path for path in temp_extract_dir.iterdir() if path.is_dir()]
    if len(extracted_roots) != 1:
        raise RuntimeError(f"unexpected extracted source layout in {temp_extract_dir}")
    if destination.exists():
        shutil.rmtree(destination)
    extracted_roots[0].rename(destination)
    shutil.rmtree(temp_extract_dir)


def run_json_command(command: list[str], command_runner: CommandRunner) -> dict[str, Any]:
    stdout = command_runner(command, True)
    if not stdout:
        raise RuntimeError(f"command returned empty JSON output: {command!r}")
    loaded = cast(object, json.loads(stdout))
    if not isinstance(loaded, dict):
        raise RuntimeError("expected JSON object")
    return cast(dict[str, Any], loaded)


def default_command_runner(command: list[str], capture_output: bool) -> str | None:
    completed = subprocess.run(
        command,
        check=True,
        cwd=ROOT_DIR,
        capture_output=capture_output,
        text=capture_output,
    )
    if capture_output:
        return completed.stdout
    return None


def default_downloader(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as response:
        destination.write_bytes(response.read())


def default_status_checker(wda_url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{wda_url.rstrip('/')}/status", timeout=2.0) as response:
            return response.status == 200
    except (urllib.error.URLError, ConnectionResetError, TimeoutError, OSError):
        return False
