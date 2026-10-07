from __future__ import annotations

from munk.config import ResolvedConfig
from munk.optimizing.errors import OptimizeRuntimeUnavailableError
from munk.optimizing.runtime import create_optimize_runtime, diagnose_optimize_runtime


def resolve_optimize_runtime(*, resolved_config: ResolvedConfig):
    try:
        return create_optimize_runtime(resolved_config=resolved_config)
    except LookupError as exc:
        raise OptimizeRuntimeUnavailableError(str(exc)) from exc


def optimize_runtime_health():
    return diagnose_optimize_runtime()
