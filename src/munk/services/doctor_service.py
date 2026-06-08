from __future__ import annotations

from munk.config.schema import MunkConfig
from munk.paths import adb_path
from munk.services.models import DoctorResult
from munk.services.perception_runtime import diagnose_perception_runtime


def review_runtime_health():
    from munk.services.review_runtime import review_runtime_health as _review_runtime_health

    return _review_runtime_health()


class DoctorService:
    def run(self) -> DoctorResult:
        adb = adb_path()
        missing: list[str] = []
        diagnostics = None
        if not adb.exists():
            missing.append(f"adb missing: {adb}")
        try:
            diagnostics = diagnose_perception_runtime(MunkConfig())
        except Exception as exc:  # noqa: BLE001
            missing.append(str(exc))
        else:
            missing.extend(diagnostics.missing_items)
        try:
            review_health = review_runtime_health()
        except ModuleNotFoundError:
            review_health = None
        except Exception as exc:  # noqa: BLE001
            missing.append(str(exc))
        else:
            if review_health.status != "ok":
                missing.append(f"review runtime check failed: {review_health.message}")
        return DoctorResult(
            adb_path=adb,
            perception_diagnostics=diagnostics,
            missing_items=missing,
        )
