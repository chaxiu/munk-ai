from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from munk.app import AppTarget
from munk.device import DeviceDriver, SupportsAppLifecycle, SupportsDeviceLockState, SupportsDeviceUnlock
from munk.services.errors import StartStateError
from munk.testing import TestCase, normalize_case_page_id

StartStateStepKind = Literal["unlock", "app_reset", "page_navigation"]
StartStateStepOutcome = Literal["succeeded", "failed", "skipped"]


class PageNavigator(Protocol):
    def __call__(
        self,
        *,
        device: DeviceDriver,
        app_target: AppTarget,
        page_id: str,
        case: TestCase,
    ) -> None: ...


class StartStateProgressEmitter(Protocol):
    def __call__(
        self,
        *,
        event_type: str,
        message: str,
        summary: str,
        data: dict[str, Any] | None = None,
    ) -> None: ...


@dataclass(frozen=True)
class StartStateStepPlan:
    step_kind: StartStateStepKind


@dataclass
class StartStateStepDiagnostic:
    step_index: int
    step_total: int
    step_kind: StartStateStepKind
    outcome: StartStateStepOutcome = "succeeded"
    duration_ms: int = 0
    error_message: str | None = None
    skip_reason: str | None = None
    was_locked: bool | None = None
    start_mode: str | None = None
    entry_identity: str | None = None
    page_id: str | None = None
    app_id: str | None = None


_PAGE_NAVIGATORS: dict[str, PageNavigator] = {}


def register_page_navigator(app_id: str, navigator: PageNavigator) -> None:
    _PAGE_NAVIGATORS[app_id] = navigator


def prepare_case_start_state(
    *,
    device: DeviceDriver,
    case: TestCase,
    app_target: AppTarget,
    navigator_lookup: Callable[[str], PageNavigator | None] | None = None,
    emit_progress: StartStateProgressEmitter | None = None,
) -> None:
    emit_progress = emit_progress or _noop_emit_progress
    plan = _build_start_state_plan(case)
    step_total = len(plan)
    start_state_started_at = time.monotonic()

    emit_progress(
        event_type="context_prepare_start_state_started",
        message="context prepare start state started",
        summary="case start state started",
        data={"step_count": step_total},
    )

    for index, step_plan in enumerate(plan):
        step_started_at = time.monotonic()
        diagnostic, error = _execute_start_state_step_diagnostic(
            step_plan=step_plan,
            device=device,
            case=case,
            app_target=app_target,
            navigator_lookup=navigator_lookup,
            step_index=index,
            step_total=step_total,
        )
        diagnostic.duration_ms = max(0, int((time.monotonic() - step_started_at) * 1000))
        summary = _build_step_summary(diagnostic)
        emit_progress(
            event_type="context_prepare_start_state_step",
            message=f"context prepare start state step {index + 1}/{step_total}: {summary}",
            summary=summary,
            data=_build_step_payload(diagnostic),
        )
        if error is not None:
            raise error

    start_state_duration_ms = max(0, int((time.monotonic() - start_state_started_at) * 1000))
    emit_progress(
        event_type="context_prepare_start_state_ready",
        message="context prepare start state completed",
        summary="case start state prepared",
        data={"step_count": step_total, "duration_ms": start_state_duration_ms},
    )


def _build_start_state_plan(case: TestCase) -> list[StartStateStepPlan]:
    plan = [
        StartStateStepPlan(step_kind="unlock"),
        StartStateStepPlan(step_kind="app_reset"),
    ]
    page_id = normalize_case_page_id(case.start_state.page_id)
    if page_id is not None:
        plan.append(StartStateStepPlan(step_kind="page_navigation"))
    return plan


def _execute_start_state_step_diagnostic(
    *,
    step_plan: StartStateStepPlan,
    device: DeviceDriver,
    case: TestCase,
    app_target: AppTarget,
    navigator_lookup: Callable[[str], PageNavigator | None] | None,
    step_index: int,
    step_total: int,
) -> tuple[StartStateStepDiagnostic, StartStateError | None]:
    if step_plan.step_kind == "unlock":
        return _execute_unlock_step_diagnostic(
            device=device,
            step_index=step_index,
            step_total=step_total,
        )
    if step_plan.step_kind == "app_reset":
        return _execute_app_reset_step_diagnostic(
            device=device,
            case=case,
            app_target=app_target,
            step_index=step_index,
            step_total=step_total,
        )
    return _execute_page_navigation_step_diagnostic(
        device=device,
        case=case,
        app_target=app_target,
        navigator_lookup=navigator_lookup,
        step_index=step_index,
        step_total=step_total,
    )


def _execute_unlock_step_diagnostic(
    *,
    device: DeviceDriver,
    step_index: int,
    step_total: int,
) -> tuple[StartStateStepDiagnostic, StartStateError | None]:
    diagnostic = StartStateStepDiagnostic(
        step_index=step_index,
        step_total=step_total,
        step_kind="unlock",
    )
    if not isinstance(device, SupportsDeviceUnlock):
        diagnostic.outcome = "skipped"
        diagnostic.skip_reason = "device_not_supported"
        return diagnostic, None

    was_locked: bool | None = None
    if isinstance(device, SupportsDeviceLockState):
        was_locked = device.is_locked()
        diagnostic.was_locked = was_locked
        if was_locked is False:
            diagnostic.outcome = "skipped"
            diagnostic.skip_reason = "already_unlocked"
            return diagnostic, None

    try:
        device.unlock()
    except Exception as exc:
        diagnostic.outcome = "failed"
        diagnostic.error_message = str(exc)
        return diagnostic, StartStateError(f"start state unlock failed: {exc}")

    diagnostic.outcome = "succeeded"
    return diagnostic, None


def _execute_app_reset_step_diagnostic(
    *,
    device: DeviceDriver,
    case: TestCase,
    app_target: AppTarget,
    step_index: int,
    step_total: int,
) -> tuple[StartStateStepDiagnostic, StartStateError | None]:
    start_state = case.start_state
    diagnostic = StartStateStepDiagnostic(
        step_index=step_index,
        step_total=step_total,
        step_kind="app_reset",
        start_mode=start_state.mode,
        entry_identity=app_target.entry_identity or None,
    )
    if start_state.mode != "reset":
        diagnostic.outcome = "skipped"
        diagnostic.skip_reason = "resume_mode"
        return diagnostic, None
    if not isinstance(device, SupportsAppLifecycle):
        diagnostic.outcome = "skipped"
        diagnostic.skip_reason = "device_not_supported"
        return diagnostic, None
    if not app_target.entry_identity:
        diagnostic.outcome = "skipped"
        diagnostic.skip_reason = "missing_entry_identity"
        return diagnostic, None

    try:
        device.app_stop(app_target.entry_identity)
        device.app_start(app_target.entry_identity)
    except Exception as exc:
        diagnostic.outcome = "failed"
        diagnostic.error_message = str(exc)
        return diagnostic, StartStateError(f"start state app reset failed: {exc}")

    diagnostic.outcome = "succeeded"
    return diagnostic, None


def _execute_page_navigation_step_diagnostic(
    *,
    device: DeviceDriver,
    case: TestCase,
    app_target: AppTarget,
    navigator_lookup: Callable[[str], PageNavigator | None] | None,
    step_index: int,
    step_total: int,
) -> tuple[StartStateStepDiagnostic, StartStateError | None]:
    page_id = normalize_case_page_id(case.start_state.page_id)
    diagnostic = StartStateStepDiagnostic(
        step_index=step_index,
        step_total=step_total,
        step_kind="page_navigation",
        page_id=page_id,
        app_id=app_target.app_id,
    )
    if page_id is None:
        diagnostic.outcome = "failed"
        diagnostic.error_message = "page_id is required for page navigation step"
        return diagnostic, StartStateError(diagnostic.error_message)

    lookup = navigator_lookup or _PAGE_NAVIGATORS.get
    navigator = lookup(app_target.app_id)
    if navigator is None:
        message = (
            f"case start_state.page_id '{page_id}' requires a registered page navigator "
            f"for app '{app_target.app_id}'"
        )
        diagnostic.outcome = "failed"
        diagnostic.error_message = message
        return diagnostic, StartStateError(message)

    try:
        navigator(
            device=device,
            app_target=app_target,
            page_id=page_id,
            case=case,
        )
    except Exception as exc:
        diagnostic.outcome = "failed"
        diagnostic.error_message = str(exc)
        return diagnostic, StartStateError(f"start state page navigation failed: {exc}")

    diagnostic.outcome = "succeeded"
    return diagnostic, None


def _build_step_payload(diagnostic: StartStateStepDiagnostic) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "step_index": diagnostic.step_index,
        "step_total": diagnostic.step_total,
        "step_kind": diagnostic.step_kind,
        "outcome": diagnostic.outcome,
        "duration_ms": diagnostic.duration_ms,
    }
    if diagnostic.error_message is not None:
        payload["error_message"] = diagnostic.error_message
    if diagnostic.skip_reason is not None:
        payload["skip_reason"] = diagnostic.skip_reason
    if diagnostic.was_locked is not None:
        payload["was_locked"] = diagnostic.was_locked
    if diagnostic.start_mode is not None:
        payload["start_mode"] = diagnostic.start_mode
    if diagnostic.entry_identity is not None:
        payload["entry_identity"] = diagnostic.entry_identity
    if diagnostic.page_id is not None:
        payload["page_id"] = diagnostic.page_id
    if diagnostic.app_id is not None:
        payload["app_id"] = diagnostic.app_id
    return payload


def _build_step_summary(diagnostic: StartStateStepDiagnostic) -> str:
    if diagnostic.step_kind == "unlock":
        if diagnostic.outcome == "skipped":
            reason = diagnostic.skip_reason or "skipped"
            return f"unlock device → skipped ({reason})"
        if diagnostic.outcome == "failed":
            return "unlock device → failed"
        return "unlock device → unlocked"

    if diagnostic.step_kind == "app_reset":
        identity = diagnostic.entry_identity or "app"
        if diagnostic.outcome == "skipped":
            reason = diagnostic.skip_reason or "skipped"
            return f"reset {identity} → skipped ({reason})"
        if diagnostic.outcome == "failed":
            return f"reset {identity} → failed"
        return f"reset {identity} → stop + start"

    page_id = diagnostic.page_id or "page"
    if diagnostic.outcome == "failed":
        return f"navigate to {page_id} → failed"
    return f"navigate to {page_id}"


def _noop_emit_progress(**_: object) -> None:
    return None
