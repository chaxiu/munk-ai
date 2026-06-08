from __future__ import annotations

from munk.config import ResolvedConfig
from munk.reviewing.errors import ReviewRuntimeUnavailableError
from munk.reviewing.health import ReviewRuntimeHealth
from munk.reviewing.runtime import create_review_runtime, diagnose_review_runtime


def resolve_review_runtime(*, resolved_config: ResolvedConfig):
    try:
        return create_review_runtime(resolved_config=resolved_config)
    except LookupError as exc:
        raise ReviewRuntimeUnavailableError(str(exc)) from exc


def review_runtime_health() -> ReviewRuntimeHealth:
    return diagnose_review_runtime()
