from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from uuid import uuid4

from munk.app import AppTarget
from munk.config import ResolvedConfig
from munk.config.defaults import DEFAULT_RUNNER_MAX_ELEMENTS
from munk.runtime_defaults import DEFAULT_ICON_CONF, DEFAULT_MAX_SIDE

from .device_claim_service import InteractiveDeviceClaimService
from .helpers import append_action_step, append_observation_step, close_interactive_context
from .models import (
    InteractiveActionResult,
    InteractiveObservation,
    InteractiveSession,
    InteractiveSessionStatus,
    now_iso,
)
from .session_context import InteractiveSessionContext, build_interactive_session_context
from .session_registry import InteractiveSessionEntry, InteractiveSessionRegistry

ContextBuilder = Callable[..., InteractiveSessionContext]
DEFAULT_INTERACTIVE_MAX_STEPS = 200
DEFAULT_INTERACTIVE_TTL = timedelta(minutes=30)
DEFAULT_INTERACTIVE_IDLE_TIMEOUT = timedelta(minutes=10)


class InteractiveSessionService:
    def __init__(
        self,
        registry: InteractiveSessionRegistry | None = None,
        *,
        context_builder: ContextBuilder = build_interactive_session_context,
        claim_service: InteractiveDeviceClaimService | None = None,
    ) -> None:
        self._registry = registry or InteractiveSessionRegistry()
        self._context_builder = context_builder
        self._claim_service = claim_service or InteractiveDeviceClaimService()

    @property
    def registry(self) -> InteractiveSessionRegistry:
        return self._registry

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
        max_steps: int = DEFAULT_INTERACTIVE_MAX_STEPS,
    ) -> InteractiveSession:
        self.sweep_expired()
        session_id = session_id or self._new_session_id()
        started_at = now_iso()
        session = InteractiveSession(
            session_id=session_id,
            platform=app_target.platform,
            app_target=app_target,
            device_ref=device_ref,
            claim_owner_id=session_id,
            status="created",
            max_steps=max_steps,
            started_at=started_at,
            updated_at=started_at,
            last_active_at=started_at,
            expires_at=self._add_duration(started_at, DEFAULT_INTERACTIVE_TTL),
            idle_expires_at=self._add_duration(started_at, DEFAULT_INTERACTIVE_IDLE_TIMEOUT),
        )
        self._claim_service.cleanup_for_request(device_ref)
        self._claim_service.claim_for_session(session)
        try:
            context = self._context_builder(
                resolved_config=resolved_config,
                app_target=app_target,
                device_ref=device_ref,
                max_side=max_side,
                icon_conf=icon_conf,
                max_elements=max_elements,
            )
            self._registry.create(InteractiveSessionEntry(session=session, context=context))
            self._transition(session, "waiting_agent", timestamp=started_at)
            self._claim_service.refresh_session(session)
            return session
        except Exception as exc:
            self._release_claim(
                session,
                terminal_status="failed",
                error_code="interactive_session_start_failed",
                error_message=str(exc),
            )
            raise

    def get_session(self, session_id: str) -> InteractiveSession:
        self.sweep_expired()
        session = self._registry.get(session_id)
        if session.status in {"created", "waiting_agent", "acting"}:
            self._touch_session(session)
        return session

    def get_active_entry(self, session_id: str) -> InteractiveSessionEntry:
        self.sweep_expired()
        entry = self._registry.get_active_entry(session_id)
        self._touch_session(entry.session)
        return entry

    def list_sessions(
        self,
        *,
        platform: str | None = None,
        device_ref: str | None = None,
        app_id: str | None = None,
    ) -> list[InteractiveSession]:
        self.sweep_expired()
        sessions = self._registry.list_active()
        if platform is not None:
            sessions = [session for session in sessions if session.platform == platform]
        if device_ref is not None:
            sessions = [session for session in sessions if session.device_ref == device_ref]
        if app_id is not None:
            sessions = [session for session in sessions if session.app_target.app_id == app_id]
        return sessions

    def begin_observation(self, session_id: str) -> InteractiveSessionEntry:
        entry = self.get_active_entry(session_id)
        self._ensure_ready_for_next_step(entry.session)
        return entry

    def record_observation_step(
        self,
        session_id: str,
        observation: InteractiveObservation,
    ) -> InteractiveObservation:
        entry = self.get_active_entry(session_id)
        append_observation_step(entry.session, observation)
        self._refresh_activity(entry.session, observation.captured_at)
        self._transition(entry.session, "waiting_agent", timestamp=observation.captured_at)
        return observation

    def begin_action(self, session_id: str) -> InteractiveSessionEntry:
        entry = self.get_active_entry(session_id)
        self._ensure_ready_for_next_step(entry.session)
        self._transition(entry.session, "acting")
        return entry

    def record_action_step(
        self,
        session_id: str,
        action_result: InteractiveActionResult,
    ) -> InteractiveActionResult:
        entry = self.get_active_entry(session_id)
        append_action_step(
            entry.session,
            timestamp=action_result.after.captured_at,
            summary=action_result.effect_summary,
            action_type=action_result.action.type,
            action_result=action_result,
        )
        self._refresh_activity(entry.session, entry.session.updated_at)
        self._transition(entry.session, "waiting_agent", timestamp=entry.session.updated_at)
        return action_result

    def abort_session(self, session_id: str) -> InteractiveSession:
        self.sweep_expired()
        session = self._registry.get_any_session(session_id)
        if session.status == "aborted":
            return session
        if session.status == "finalized":
            raise RuntimeError(f"interactive session already finalized: {session_id}")
        if session.status == "expired":
            raise RuntimeError(f"interactive session already expired: {session_id}")
        entry = self._registry.get_active_entry(session_id)
        session = entry.session
        self._transition(session, "aborted")
        close_interactive_context(entry.context)
        self._release_claim(session, terminal_status="cancelled")
        self._registry.complete(session)
        return session

    def finalize_session(self, session_id: str) -> InteractiveSession:
        self.sweep_expired()
        session = self._registry.get_any_session(session_id)
        if session.status == "finalized":
            return session
        if session.status == "aborted":
            raise RuntimeError(f"interactive session already aborted: {session_id}")
        if session.status == "expired":
            raise RuntimeError(f"interactive session already expired: {session_id}")
        entry = self._registry.get_active_entry(session_id)
        session = entry.session
        self._transition(session, "finalized")
        close_interactive_context(entry.context)
        self._release_claim(session, terminal_status="succeeded")
        self._registry.complete(session)
        return session

    def sweep_expired(self) -> list[InteractiveSession]:
        now = now_iso()
        expired_entries = self._registry.sweep_expired(now)
        expired_sessions: list[InteractiveSession] = []
        for entry in expired_entries:
            self._transition(entry.session, "expired", timestamp=now)
            close_interactive_context(entry.context)
            self._release_claim(
                entry.session,
                terminal_status="failed",
                error_code="interactive_session_expired",
                error_message="interactive session lease expired",
            )
            self._registry.complete(entry.session)
            expired_sessions.append(entry.session)
        return expired_sessions

    @staticmethod
    def _new_session_id() -> str:
        return f"isess_{uuid4().hex[:12]}"

    @staticmethod
    def _add_duration(timestamp: str, duration: timedelta) -> str:
        return (datetime.fromisoformat(timestamp) + duration).isoformat()

    def _refresh_activity(self, session: InteractiveSession, timestamp: str) -> None:
        session.last_active_at = timestamp
        session.idle_expires_at = self._add_duration(timestamp, DEFAULT_INTERACTIVE_IDLE_TIMEOUT)
        self._claim_service.refresh_session(session)

    def _ensure_ready_for_next_step(self, session: InteractiveSession) -> None:
        if session.status in {"finalized", "aborted", "expired"}:
            raise RuntimeError(f"interactive session is not active: {session.session_id}")
        if session.status == "acting":
            raise RuntimeError(f"interactive session is already acting: {session.session_id}")
        if session.step_count >= session.max_steps:
            self._expire_session(session.session_id, reason="step budget exceeded")

    def _expire_session(self, session_id: str, *, reason: str) -> None:
        entry = self._registry.get_active_entry(session_id)
        session = entry.session
        self._transition(session, "expired")
        close_interactive_context(entry.context)
        self._release_claim(
            session,
            terminal_status="failed",
            error_code="interactive_session_expired",
            error_message=reason,
        )
        self._registry.complete(session)
        raise RuntimeError(f"interactive session expired: {session_id}; reason={reason}")

    def _touch_session(self, session: InteractiveSession) -> None:
        self._refresh_activity(session, now_iso())

    def _release_claim(
        self,
        session: InteractiveSession,
        *,
        terminal_status: str,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        self._claim_service.release_for_session(
            session,
            terminal_status=terminal_status,
            error_code=error_code,
            error_message=error_message,
        )

    @staticmethod
    def _transition(
        session: InteractiveSession,
        status: InteractiveSessionStatus,
        *,
        timestamp: str | None = None,
    ) -> None:
        session.status = status
        session.updated_at = timestamp or now_iso()
