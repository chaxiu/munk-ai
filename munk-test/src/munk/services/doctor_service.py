from __future__ import annotations

from munk.config.schema import MunkConfig
from munk.paths import adb_path
from munk.perception.diagnostics import PerceptionProviderDiagnostics
from munk.services import playwright_browser_env as playwright_browsers
from munk.services.models import DoctorResult
from munk.services.perception_runtime import diagnose_perception_runtime
from munk.services.playwright_browser_env import (
    PlaywrightBrowserDiagnostics,
    PlaywrightBrowserEnvError,
    ProgressReporter,
)


def review_runtime_health():
    from munk.services.review_runtime import review_runtime_health as _review_runtime_health

    return _review_runtime_health()


class DoctorService:
    def run(
        self,
        *,
        fix: bool = False,
        on_progress: ProgressReporter | None = None,
    ) -> DoctorResult:
        missing: list[str] = []
        if fix:
            missing.extend(_apply_fixes(on_progress=on_progress))

        adb = adb_path()
        if not adb.exists():
            missing.append(f"adb missing: {adb}")

        diagnostics, perception_missing = _collect_perception_diagnostics()
        missing.extend(perception_missing)
        missing.extend(_collect_review_missing_items())
        playwright_diagnostics, playwright_missing = _collect_playwright_diagnostics()
        missing.extend(playwright_missing)

        return DoctorResult(
            adb_path=adb,
            perception_diagnostics=diagnostics,
            playwright_diagnostics=playwright_diagnostics,
            missing_items=missing,
        )


def _apply_fixes(*, on_progress: ProgressReporter | None) -> list[str]:
    """Apply all auto-fixable doctor repairs, then let run() re-check."""
    failures: list[str] = []
    failures.extend(_fix_playwright_chromium(on_progress=on_progress))
    return failures


def _fix_playwright_chromium(*, on_progress: ProgressReporter | None) -> list[str]:
    try:
        playwright_browsers.ensure_chromium(on_progress=on_progress)
    except PlaywrightBrowserEnvError as exc:
        return [str(exc)]
    except Exception as exc:  # noqa: BLE001
        return [f"playwright chromium fix failed: {exc}"]
    return []


def _collect_perception_diagnostics() -> tuple[PerceptionProviderDiagnostics | None, list[str]]:
    try:
        diagnostics = diagnose_perception_runtime(MunkConfig())
    except Exception as exc:  # noqa: BLE001
        return None, [str(exc)]
    return diagnostics, list(diagnostics.missing_items)


def _collect_review_missing_items() -> list[str]:
    try:
        review_health = review_runtime_health()
    except ModuleNotFoundError:
        return []
    except Exception as exc:  # noqa: BLE001
        return [str(exc)]
    if review_health.status != "ok":
        return [f"review runtime check failed: {review_health.message}"]
    return []


def _collect_playwright_diagnostics() -> tuple[PlaywrightBrowserDiagnostics | None, list[str]]:
    try:
        diagnostics = playwright_browsers.diagnose()
    except Exception as exc:  # noqa: BLE001
        return None, [f"playwright browser check failed: {exc}"]
    return diagnostics, list(diagnostics.missing_items)
