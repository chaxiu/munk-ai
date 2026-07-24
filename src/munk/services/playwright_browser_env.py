from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from munk.user_data import cache_home

ENV_PLAYWRIGHT_BROWSERS_PATH = "PLAYWRIGHT_BROWSERS_PATH"
FIX_COMMAND = "munk doctor --fix"
BROWSERS_CACHE_DIRNAME = "playwright-browsers"


def empty_notes() -> list[str]:
    return []


def empty_missing_items() -> list[str]:
    return []


@dataclass(frozen=True)
class PlaywrightBrowserDiagnostics:
    browsers_dir: Path
    chromium_ready: bool
    chromium_executable: Path | None = None
    missing_items: list[str] = field(default_factory=empty_missing_items)
    notes: list[str] = field(default_factory=empty_notes)


class PlaywrightBrowserEnvError(RuntimeError):
    """Raised when Playwright Chromium cannot be prepared."""


def browsers_dir() -> Path:
    # Persist across munk version upgrades; Playwright still keys builds by revision.
    return cache_home() / BROWSERS_CACHE_DIRNAME


def export_playwright_env() -> Path:
    resolved = browsers_dir()
    os.environ[ENV_PLAYWRIGHT_BROWSERS_PATH] = str(resolved)
    return resolved


def diagnose() -> PlaywrightBrowserDiagnostics:
    browsers = export_playwright_env()
    missing: list[str] = []
    notes: list[str] = []
    executable: Path | None = None
    ready = False
    try:
        executable = _chromium_executable_path()
    except Exception as exc:  # noqa: BLE001
        missing.append(
            f"playwright chromium unavailable: {exc}; run: {FIX_COMMAND}"
        )
    else:
        if executable is not None and executable.exists():
            ready = True
        else:
            missing.append(
                f"playwright chromium missing: {browsers}; run: {FIX_COMMAND}"
            )
    if sys.platform.startswith("linux"):
        notes.append(
            "Linux system libraries may be required for Chromium; "
            f"run: {sys.executable} -m playwright install-deps chromium (requires root)"
        )
    return PlaywrightBrowserDiagnostics(
        browsers_dir=browsers,
        chromium_ready=ready,
        chromium_executable=executable,
        missing_items=missing,
        notes=notes,
    )


def ensure_chromium(*, force: bool = False) -> Path:
    browsers = export_playwright_env()
    if not force:
        current = diagnose()
        if current.chromium_ready:
            return browsers
    try:
        _install_chromium(browsers_dir=browsers)
    except PlaywrightBrowserEnvError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise PlaywrightBrowserEnvError(
            f"failed to install playwright chromium into {browsers}: {exc}; "
            f"run: {FIX_COMMAND}"
        ) from exc
    after = diagnose()
    if not after.chromium_ready:
        detail = "; ".join(after.missing_items) if after.missing_items else "chromium still missing"
        raise PlaywrightBrowserEnvError(
            f"playwright chromium install did not produce a usable browser at {browsers}: "
            f"{detail}; run: {FIX_COMMAND}"
        )
    return browsers


def _chromium_executable_path() -> Path | None:
    from playwright.sync_api import sync_playwright  # pyright: ignore[reportMissingImports]

    manager = sync_playwright()
    playwright = manager.start()
    try:
        raw = getattr(playwright.chromium, "executable_path", None)
        if not isinstance(raw, str) or not raw.strip():
            return None
        return Path(raw)
    finally:
        playwright.stop()


def _install_chromium(*, browsers_dir: Path) -> None:
    browsers_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env[ENV_PLAYWRIGHT_BROWSERS_PATH] = str(browsers_dir)
    command = [sys.executable, "-m", "playwright", "install", "chromium"]
    completed = subprocess.run(  # noqa: S603
        command,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode == 0:
        return
    stderr = (completed.stderr or "").strip()
    stdout = (completed.stdout or "").strip()
    detail = stderr or stdout or f"exit code {completed.returncode}"
    raise PlaywrightBrowserEnvError(
        f"playwright install chromium failed for {browsers_dir}: {detail}; "
        f"run: {FIX_COMMAND}"
    )
