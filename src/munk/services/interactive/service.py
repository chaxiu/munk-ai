from __future__ import annotations

from munk.app import AppTarget
from munk.config import ResolvedConfig
from munk.config.defaults import DEFAULT_RUNNER_MAX_ELEMENTS
from munk.runtime_defaults import DEFAULT_ICON_CONF, DEFAULT_MAX_SIDE

from .action_service import InteractiveActionService
from .device_claim_service import InteractiveDeviceClaimService
from .models import (
    InteractiveActionRequest,
    InteractiveActionResult,
    InteractiveFinalizeResult,
    InteractiveObservation,
    InteractiveSession,
)
from .observation_service import InteractiveObservationService
from .report_service import InteractiveReportService
from .session_context import build_interactive_session_context
from .session_registry import InteractiveSessionRegistry
from .session_service import ContextBuilder, InteractiveSessionService


class InteractiveService:
    def __init__(
        self,
        registry: InteractiveSessionRegistry | None = None,
        *,
        context_builder: ContextBuilder | None = None,
        claim_service: InteractiveDeviceClaimService | None = None,
    ) -> None:
        registry = registry or InteractiveSessionRegistry()
        self._session_service = InteractiveSessionService(
            registry,
            context_builder=context_builder or build_interactive_session_context,
            claim_service=claim_service,
        )
        self._observation_service = InteractiveObservationService(self._session_service)
        self._action_service = InteractiveActionService(self._session_service)
        self._report_service = InteractiveReportService(self._session_service)

    def start_session(
        self,
        *,
        resolved_config: ResolvedConfig,
        app_target: AppTarget,
        device_ref: str | None = None,
        session_id: str | None = None,
        max_side: int = DEFAULT_MAX_SIDE,
        icon_conf: float = DEFAULT_ICON_CONF,
        max_elements: int = DEFAULT_RUNNER_MAX_ELEMENTS,
    ) -> InteractiveSession:
        return self._session_service.start_session(
            resolved_config=resolved_config,
            app_target=app_target,
            device_ref=device_ref,
            session_id=session_id,
            max_side=max_side,
            icon_conf=icon_conf,
            max_elements=max_elements,
        )

    def get_session(self, session_id: str) -> InteractiveSession:
        return self._session_service.get_session(session_id)

    def list_sessions(
        self,
        *,
        platform: str | None = None,
        device_ref: str | None = None,
        app_id: str | None = None,
    ) -> list[InteractiveSession]:
        return self._session_service.list_sessions(
            platform=platform,
            device_ref=device_ref,
            app_id=app_id,
        )

    def observe(self, session_id: str) -> InteractiveObservation:
        return self._observation_service.observe(session_id)

    def act(
        self,
        session_id: str,
        action_request: InteractiveActionRequest,
        settle_timeout_sec: float | None = None,
    ) -> InteractiveActionResult:
        return self._action_service.act(
            session_id,
            action_request,
            settle_timeout_sec=settle_timeout_sec,
        )

    def abort(self, session_id: str) -> InteractiveSession:
        return self._session_service.abort_session(session_id)

    def finalize(
        self,
        session_id: str,
        summary: str | None = None,
    ) -> InteractiveFinalizeResult:
        return self._report_service.finalize(session_id, summary)
