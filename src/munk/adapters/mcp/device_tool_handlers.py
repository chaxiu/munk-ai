from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from munk.adapters.shared.app_lifecycle import AppLifecycleResult, AppLifecycleService
from munk.adapters.shared.device_queries import list_devices_payload
from munk.adapters.shared.machine_requests import AppInstallRequest, AppLaunchRequest, AppStopRequest
from munk.agent_base.action import Action, ActionType
from munk.config.runtime import require_config_context
from munk.services.app_target_resolver import resolve_app_target_for_execution
from munk.services.errors import DeviceConflictError
from munk.services.interactive import (
    InteractiveActionRequest,
    InteractiveActionResult,
    InteractiveService,
    InteractiveSession,
)

from .device_tool_models import (
    AppInstallInput,
    AppLaunchInput,
    AppStopInput,
    DevicesListInput,
    SessionAbortInput,
    SessionActInput,
    SessionActionInput,
    SessionFinalizeInput,
    SessionGetInput,
    SessionObserveInput,
    SessionsListInput,
    SessionStartInput,
)
from .device_tool_outputs import (
    AppLifecycleData,
    AppLifecycleOutput,
    DevicesListOutput,
    InteractiveActionData,
    InteractiveSessionData,
    InteractiveSessionListItemData,
    SessionAbortOutput,
    SessionActOutput,
    SessionFinalizeOutput,
    SessionGetOutput,
    SessionObserveOutput,
    SessionsListOutput,
    SessionStartConflictData,
    SessionStartOutput,
)
from .interactive_projection import build_observation_payload


class DeviceMcpToolHandlers:
    def __init__(
        self,
        *,
        interactive_service_factory: Callable[[], InteractiveService],
        app_lifecycle_service_factory: Callable[[], AppLifecycleService] | None = None,
        workspace_root: Callable[[], Path] | None = None,
    ) -> None:
        self._interactive_service_factory = interactive_service_factory
        self._app_lifecycle_service_factory = app_lifecycle_service_factory or AppLifecycleService
        self._workspace_root = workspace_root or Path.cwd

    def devices_list(self, request: DevicesListInput) -> DevicesListOutput:
        data = list_devices_payload(request.platform)
        return DevicesListOutput(summary=f"found {len(data.items)} device(s)", data=data)

    def app_launch(self, request: AppLaunchInput) -> AppLifecycleOutput:
        result = self._app_lifecycle_service_factory().launch(
            AppLaunchRequest(
                app_id=request.app_id,
                platform=request.platform,
                device_ref=request.device_ref,
                package=request.package,
                bundle_id=request.bundle_id,
                base_url=request.base_url,
                origin=request.origin,
                headless=request.headless,
                assets_root=request.assets_root,
            )
        )
        return AppLifecycleOutput(
            summary=f"launched app {result.entry_identity} on {result.platform}",
            data=_build_app_lifecycle_data(result),
        )

    def app_stop(self, request: AppStopInput) -> AppLifecycleOutput:
        result = self._app_lifecycle_service_factory().stop(
            AppStopRequest(
                app_id=request.app_id,
                platform=request.platform,
                device_ref=request.device_ref,
                package=request.package,
                bundle_id=request.bundle_id,
                base_url=request.base_url,
                origin=request.origin,
                headless=request.headless,
                assets_root=request.assets_root,
            )
        )
        return AppLifecycleOutput(
            summary=f"stopped app {result.entry_identity} on {result.platform}",
            data=_build_app_lifecycle_data(result),
        )

    def app_install(self, request: AppInstallInput) -> AppLifecycleOutput:
        result = self._app_lifecycle_service_factory().install(
            AppInstallRequest(
                app_id=request.app_id,
                artifact_path=request.artifact_path,
                platform=request.platform,
                device_ref=request.device_ref,
                package=request.package,
                bundle_id=request.bundle_id,
                base_url=request.base_url,
                origin=request.origin,
                headless=request.headless,
                assets_root=request.assets_root,
            )
        )
        return AppLifecycleOutput(
            summary=f"installed artifact for app {result.entry_identity} on {result.platform}",
            data=_build_app_lifecycle_data(result),
        )

    def session_start(self, request: SessionStartInput) -> SessionStartOutput:
        resolved_config = require_config_context(
            cli_path=request.config_path,
            workspace_root=self._workspace_root(),
            command_name="session_start",
        )
        app_target = resolve_app_target_for_execution(
            app_id=request.app_id,
            platform=request.platform,
            package=request.package,
            bundle_id=request.bundle_id,
            base_url=request.base_url,
            origin=request.origin,
            headless=request.headless,
        )
        try:
            session = self._interactive_service_factory().start_session(
                resolved_config=resolved_config,
                app_target=app_target,
                device_ref=request.device_ref,
            )
        except DeviceConflictError as exc:
            guidance = _build_session_start_conflict_data(exc)
            raise RuntimeError(
                "interactive session_start device conflict: "
                + json.dumps(guidance.model_dump(mode="json"), ensure_ascii=True, sort_keys=True)
            ) from exc
        return SessionStartOutput(
            summary=f"started interactive session {session.session_id}",
            data=_build_session_data(session),
        )

    def session_get(self, request: SessionGetInput) -> SessionGetOutput:
        session = self._interactive_service_factory().get_session(request.session_id)
        return SessionGetOutput(
            summary=f"loaded interactive session {session.session_id} with status={session.status}",
            data=_build_session_data(session),
        )

    def sessions_list(self, request: SessionsListInput) -> SessionsListOutput:
        sessions = self._interactive_service_factory().list_sessions(
            platform=request.platform,
            device_ref=request.device_ref,
            app_id=request.app_id,
        )
        data = [_build_session_list_item_data(session) for session in sessions]
        return SessionsListOutput(
            summary=f"found {len(data)} active interactive session(s)",
            data=data,
        )

    def session_observe(self, request: SessionObserveInput) -> SessionObserveOutput:
        service = self._interactive_service_factory()
        observation = service.observe(request.session_id)
        session = service.get_session(request.session_id)
        return SessionObserveOutput(
            summary=observation.summary,
            session=_build_session_data(session),
            observation=build_observation_payload(
                observation,
                detail=request.detail,
                include_screenshot=request.include_screenshot,
            ),
        )

    def session_act(self, request: SessionActInput) -> SessionActOutput:
        service = self._interactive_service_factory()
        action_request = InteractiveActionRequest(
            action=_build_action(request.action),
            target_id=request.action.target_id,
            resource_id=request.action.resource_id,
            label=request.action.label,
        )
        result = service.act(
            request.session_id,
            action_request,
            settle_timeout_sec=request.settle_timeout_sec,
        )
        session = service.get_session(request.session_id)
        return _build_session_act_output(
            session,
            result,
            request=action_request,
            detail=request.detail,
        )

    def session_finalize(self, request: SessionFinalizeInput) -> SessionFinalizeOutput:
        service = self._interactive_service_factory()
        result = service.finalize(request.session_id, request.summary)
        session = service.get_session(request.session_id)
        return SessionFinalizeOutput(
            summary=f"finalized interactive session {result.session_id}",
            session=_build_session_data(session),
            step_count=result.step_count,
            steps_summary=list(result.steps_summary),
            last_observation_summary=result.last_observation_summary,
            agent_summary=result.agent_summary,
        )

    def session_abort(self, request: SessionAbortInput) -> SessionAbortOutput:
        session = self._interactive_service_factory().abort(request.session_id)
        return SessionAbortOutput(
            summary=f"aborted interactive session {session.session_id}",
            data=_build_session_data(session),
        )


def _build_action(action: SessionActionInput) -> Action:
    return Action(
        type=ActionType(action.type),
        box=action.box,
        point=action.point,
        text=action.text,
        direction=action.direction,
        distance_px=action.distance_px,
        duration=action.duration,
        dismiss_keyboard=action.dismiss_keyboard,
        summary=action.summary,
    )


def _build_app_lifecycle_data(result: AppLifecycleResult) -> AppLifecycleData:
    return AppLifecycleData(
        action=result.action,
        app_id=result.app_id,
        platform=result.platform,
        device_ref=result.device_ref,
        entry_identity=result.entry_identity,
        artifact_path=result.artifact_path,
    )


def _build_session_act_output(
    session: InteractiveSession,
    result: InteractiveActionResult,
    *,
    request: InteractiveActionRequest,
    detail: str,
) -> SessionActOutput:
    compact = detail == "compact"
    return SessionActOutput(
        summary=result.effect_summary,
        session=_build_session_data(session),
        action=_build_action_data(
            result.action,
            target_id=request.target_id,
            resource_id=request.resource_id,
            label=request.label,
        ),
        normalized_action=_build_action_data(result.normalized_action),
        before=None if compact else build_observation_payload(result.before, detail="full"),
        after=build_observation_payload(result.after, detail="compact" if compact else "full"),
        before_summary=result.before.summary,
        after_summary=result.after.summary,
        executed=result.executed,
        timed_out=result.timed_out,
        duration_ms=result.duration_ms,
        effect_summary=result.effect_summary,
        settle_status=result.settle_status,
        settle_timed_out=result.settle_timed_out,
        settle_elapsed_ms=result.settle_elapsed_ms,
        settle_summary=result.settle_summary,
        error_type=result.error_type,
        error_message=result.error_message,
    )


def _build_session_list_item_data(session: InteractiveSession) -> InteractiveSessionListItemData:
    return InteractiveSessionListItemData(
        session_id=session.session_id,
        status=session.status,
        platform=session.platform,
        app_id=session.app_target.app_id,
        device_ref=session.device_ref,
        step_count=session.step_count,
        last_active_at=session.last_active_at,
        idle_expires_at=session.idle_expires_at,
        last_observation_summary=(
            session.last_observation.summary if session.last_observation is not None else None
        ),
    )


def _build_session_data(session: InteractiveSession) -> InteractiveSessionData:
    return InteractiveSessionData(
        session_id=session.session_id,
        status=session.status,
        platform=session.platform,
        app_id=session.app_target.app_id,
        device_ref=session.device_ref,
        step_count=session.step_count,
        started_at=session.started_at,
        updated_at=session.updated_at,
        last_active_at=session.last_active_at,
        expires_at=session.expires_at,
        idle_expires_at=session.idle_expires_at,
        last_observation_summary=(
            session.last_observation.summary if session.last_observation is not None else None
        ),
        finalized_agent_summary=(
            session.finalized_result.agent_summary
            if session.finalized_result is not None
            else None
        ),
    )


def _build_action_data(
    action: Action,
    *,
    target_id: int | None = None,
    resource_id: str | None = None,
    label: str | None = None,
) -> InteractiveActionData:
    return InteractiveActionData(
        type=action.type.value,
        target_id=target_id,
        resource_id=resource_id,
        label=label,
        box=action.box,
        point=action.point,
        text=action.text,
        start=action.start,
        end=action.end,
        duration=action.duration,
        dismiss_keyboard=action.dismiss_keyboard,
        summary=action.summary,
    )


def _build_session_start_conflict_data(exc: DeviceConflictError) -> SessionStartConflictData:
    can_resume = exc.blocking_kind == "interactive_session"
    resume_session_id = exc.blocking_operation_id if can_resume else None
    if can_resume:
        suggested_next_actions = [
            "sessions_list",
            "session_get",
            "session_observe",
            "session_finalize",
        ]
    else:
        suggested_next_actions = [
            "devices_list",
            "session_start with another device_ref",
            "wait for the blocking operation to finish",
        ]
    return SessionStartConflictData(
        requested_device_ref=exc.requested_device_ref,
        blocked_by=exc.blocking_operation_id,
        blocking_kind=exc.blocking_kind,
        blocking_status=exc.blocking_status,
        blocking_device_ref=exc.blocking_device_ref,
        reason=exc.reason,
        can_resume=can_resume,
        resume_session_id=resume_session_id,
        suggested_next_actions=suggested_next_actions,
    )
