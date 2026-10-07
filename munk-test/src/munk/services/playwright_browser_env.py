from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from munk.user_data import cache_home

ENV_PLAYWRIGHT_BROWSERS_PATH = "PLAYWRIGHT_BROWSERS_PATH"
FIX_COMMAND = "munk doctor --fix"
BROWSERS_CACHE_DIRNAME = "playwright-browsers"

ProgressReporter = Callable[[str], None]


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


def ensure_chromium(
    *,
    force: bool = False,
    on_progress: ProgressReporter | None = None,
) -> Path:
    browsers = export_playwright_env()
    if not force:
        current = diagnose()
        if current.chromium_ready:
            _emit(on_progress, f"playwright chromium already installed: {browsers}")
            return browsers
    _emit(on_progress, f"installing playwright chromium into {browsers}")
    try:
        _install_chromium(browsers_dir=browsers, on_progress=on_progress)
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
    _emit(on_progress, f"playwright chromium ready: {browsers}")
    return browsers


def _emit(on_progress: ProgressReporter | None, message: str) -> None:
    if on_progress is not None:
        on_progress(message)


_CHROMIUM_EXECUTABLE_NAMES = frozenset(
    {
        "chrome",
        "chrome.exe",
        "Chromium",
        "chromium",
        "Google Chrome for Testing",
        "headless_shell",
        "headless_shell.exe",
    }
)


def _chromium_executable_path() -> Path | None:
    cached = _find_cached_chromium_executable(browsers_dir())
    if cached is not None:
        return cached
    return _chromium_executable_path_via_playwright()


def _find_cached_chromium_executable(browsers: Path) -> Path | None:
    if not browsers.is_dir():
        return None
    matches: list[Path] = []
    for path in browsers.rglob("*"):
        if not path.is_file() or path.name not in _CHROMIUM_EXECUTABLE_NAMES:
            continue
        text = str(path)
        if "Helper" in text or "/Helpers/" in text or "\\Helpers\\" in text:
            continue
        matches.append(path)
    if not matches:
        return None
    # Prefer full Chromium over headless_shell when both exist.
    matches.sort(
        key=lambda path: (
            0 if "headless" in path.name.lower() else 1,
            0 if "chrome-mac" in str(path) or "chrome-linux" in str(path) or "chrome-win" in str(path) else 1,
            -len(str(path)),
        ),
        reverse=True,
    )
    return matches[0]


def _chromium_executable_path_via_playwright() -> Path | None:
    import asyncio

    # Playwright sync API cannot start inside a running event loop (verify ops).
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        pass
    else:
        return None

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


def _install_chromium(
    *,
    browsers_dir: Path,
    on_progress: ProgressReporter | None = None,
) -> None:
    browsers_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env[ENV_PLAYWRIGHT_BROWSERS_PATH] = str(browsers_dir)
    command = [sys.executable, "-m", "playwright", "install", "chromium"]
    if on_progress is None:
        _install_chromium_quiet(command=command, env=env, browsers_dir=browsers_dir)
        return
    _install_chromium_streaming(
        command=command,
        env=env,
        browsers_dir=browsers_dir,
        on_progress=on_progress,
    )


def _install_chromium_quiet(
    *,
    command: list[str],
    env: dict[str, str],
    browsers_dir: Path,
) -> None:
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


def _install_chromium_streaming(
    *,
    command: list[str],
    env: dict[str, str],
    browsers_dir: Path,
    on_progress: ProgressReporter,
) -> None:
    # Stream Playwright's own download/extract logs so long installs stay visible.
    # Prefer line-oriented forwarding; keep a trailing buffer for final incomplete lines.
    process = subprocess.Popen(  # noqa: S603
        command,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    collected: list[str] = []
    assert process.stdout is not None
    try:
        for raw_line in process.stdout:
            collected.append(raw_line)
            for piece in raw_line.replace("\r", "\n").split("\n"):
                text = piece.strip()
                if text:
                    on_progress(text)
    finally:
        process.stdout.close()
    returncode = process.wait()
    if returncode == 0:
        return
    detail = "".join(collected).strip() or f"exit code {returncode}"
    raise PlaywrightBrowserEnvError(
        f"playwright install chromium failed for {browsers_dir}: {detail}; "
        f"run: {FIX_COMMAND}"
    )
