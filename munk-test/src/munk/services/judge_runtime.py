from __future__ import annotations

from munk.config import ResolvedConfig
from munk.judging.errors import JudgeRuntimeUnavailableError
from munk.judging.health import JudgeRuntimeHealth
from munk.judging.runtime import create_judge_runtime, diagnose_judge_runtime


def resolve_judge_runtime(*, resolved_config: ResolvedConfig):
    try:
        return create_judge_runtime(resolved_config=resolved_config)
    except LookupError as exc:
        raise JudgeRuntimeUnavailableError(str(exc)) from exc


def judge_runtime_health() -> JudgeRuntimeHealth:
    return diagnose_judge_runtime()
