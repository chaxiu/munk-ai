from __future__ import annotations

from typing import Any

from munk.judging.health import JudgeRuntimeHealth

from .service import JudgeRuntimeService


class LocalJudgeRuntime:
    runtime_id = "local"

    def __init__(self, *, resolved_config: Any) -> None:
        self._service = JudgeRuntimeService(resolved_config=resolved_config)

    def judge(self, request, *, context, cancel_controller=None):  # noqa: ANN001
        return self._service.judge(request, context=context, cancel_controller=cancel_controller)


class LocalJudgeRuntimeFactory:
    runtime_id = "local"

    def create_runtime(self, *, resolved_config: Any) -> LocalJudgeRuntime:
        return LocalJudgeRuntime(resolved_config=resolved_config)

    def diagnose(self) -> JudgeRuntimeHealth:
        return JudgeRuntimeHealth(runtime_id=self.runtime_id, status="ok", message="judge local runtime is available")


def build_judge_runtime_factory() -> LocalJudgeRuntimeFactory:
    return LocalJudgeRuntimeFactory()
