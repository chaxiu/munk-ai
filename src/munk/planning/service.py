from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from munk.app_assets.storage import AppRegistry
from munk.config import ResolvedConfig
from munk.planning.models import ChangePlanInput, RequirementInput
from munk.planning.runtime import PlanRuntime
from munk.planning.storage import CoreCaseRegistry, PlanStore
from munk.services.plan_runtime import resolve_plan_runtime
from munk.services.planning.orchestration import (
    build_plan_saved_payload,
    build_planning_storage_bundle,
    execute_plan_generation,
)
from munk.token_usage import TokenUsage

PLAN_VERSION = "v1.0"


def default_plan_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    suffix = uuid4().hex[:8]
    return f"plan_{timestamp}_{suffix}"


@dataclass(frozen=True)
class PlanGenerationResult:
    plan: Any
    plan_path: Path
    snapshot_path: Path
    planning_usage: TokenUsage | None = None


class _CallbackProgressSink:
    def __init__(self, callback: Callable[[str, str | None, dict[str, Any]], None] | None) -> None:
        self._callback = callback

    def emit(self, event) -> None:  # noqa: ANN001
        if self._callback is None:
            return
        if event.event_type in {"agent_started", "agent_ended", "agent_failed", "agent_canceled"}:
            return
        self._callback(event.event_type, event.message, dict(event.data))


class _CancelAdapter:
    def __init__(self, cancel_checker: Callable[[], bool] | None) -> None:
        self._cancel_checker = cancel_checker

    def should_cancel(self) -> bool:
        if self._cancel_checker is None:
            return False
        return self._cancel_checker()


class _DirectPlanTracker:
    def __init__(self, cancel_checker: Callable[[], bool] | None, progress_callback: Callable[[str, str | None, dict[str, Any]], None] | None) -> None:
        self.operation_id: str | None = None
        self._cancel = _CancelAdapter(cancel_checker)
        self._sink = _CallbackProgressSink(progress_callback)

    def should_cancel(self) -> bool:
        return self._cancel.should_cancel()

    def append_event(
        self,
        event_type: str,
        message: str | None,
        data: dict[str, object] | None = None,
    ) -> None:
        payload = {} if data is None else data
        self._sink.emit(type("Event", (), {"event_type": event_type, "message": message, "data": payload})())

    def update_progress(self, **kwargs) -> None:  # noqa: ANN003
        del kwargs


class PlanService:
    def __init__(
        self,
        *,
        app_registry: AppRegistry | None = None,
        core_case_registry: CoreCaseRegistry | None = None,
        plan_store: PlanStore | None = None,
        runtime_factory: Callable[[ResolvedConfig], PlanRuntime] | None = None,
    ) -> None:
        self._app_registry = app_registry or AppRegistry()
        self._core_case_registry = core_case_registry or CoreCaseRegistry()
        self._plan_store = plan_store or PlanStore()
        self._runtime_factory = runtime_factory or self._default_runtime_factory

    def generate_plan(
        self,
        request: RequirementInput,
        *,
        resolved_config: ResolvedConfig,
        cancel_checker: Callable[[], bool] | None = None,
        progress_callback: Callable[[str, str | None, dict[str, Any]], None] | None = None,
    ) -> PlanGenerationResult:
        return self._generate(request, resolved_config=resolved_config, cancel_checker=cancel_checker, progress_callback=progress_callback)

    def generate_change_plan(
        self,
        request: ChangePlanInput,
        *,
        resolved_config: ResolvedConfig,
        cancel_checker: Callable[[], bool] | None = None,
        progress_callback: Callable[[str, str | None, dict[str, Any]], None] | None = None,
    ) -> PlanGenerationResult:
        return self._generate(request, resolved_config=resolved_config, cancel_checker=cancel_checker, progress_callback=progress_callback)

    def _generate(self, request, *, resolved_config: ResolvedConfig, cancel_checker, progress_callback):  # noqa: ANN001
        tracker = _DirectPlanTracker(cancel_checker, progress_callback)
        storage = build_planning_storage_bundle(
            assets_root=getattr(request, "assets_root", None),
            default_app_registry=self._app_registry,
            default_core_case_registry=self._core_case_registry,
            default_plan_store=self._plan_store,
        )
        materialized = execute_plan_generation(
            request=request,
            tracker=tracker,
            resolved_config=resolved_config,
            storage=storage,
            runtime_factory=self._runtime_factory,
        )
        saved_event_type = "change_plan_saved" if isinstance(request, ChangePlanInput) else "plan_saved"
        if progress_callback is not None:
            progress_callback(
                saved_event_type,
                "change plan saved" if isinstance(request, ChangePlanInput) else "plan saved",
                build_plan_saved_payload(materialized),
            )
        return PlanGenerationResult(
            plan=materialized.plan,
            plan_path=materialized.plan_path,
            snapshot_path=materialized.snapshot_path,
            planning_usage=materialized.planning_usage,
        )

    @staticmethod
    def _default_runtime_factory(resolved_config: ResolvedConfig) -> PlanRuntime:
        return resolve_plan_runtime(resolved_config=resolved_config)
