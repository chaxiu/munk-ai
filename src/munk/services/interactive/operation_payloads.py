from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from munk.services.interactive.models import InteractiveSession


class InteractiveSessionOperationRequest(BaseModel):
    interactive_session_id: str
    platform: str
    device_ref: str | None = None


class InteractiveSessionStatePayload(BaseModel):
    session_id: str
    status: str
    last_active_at: str | None = None
    expires_at: str | None = None
    idle_expires_at: str | None = None


class InteractiveSessionOperationProgress(BaseModel):
    interactive_session: InteractiveSessionStatePayload


def build_interactive_session_operation_request_payload(session: InteractiveSession) -> dict[str, Any]:
    payload = InteractiveSessionOperationRequest(
        interactive_session_id=session.session_id,
        platform=session.platform,
        device_ref=session.device_ref,
    )
    return payload.model_dump(mode="json", exclude_none=True)


def build_interactive_session_progress_payload(session: InteractiveSession) -> dict[str, Any]:
    payload = InteractiveSessionOperationProgress(
        interactive_session=InteractiveSessionStatePayload(
            session_id=session.session_id,
            status=session.status,
            last_active_at=session.last_active_at,
            expires_at=session.expires_at,
            idle_expires_at=session.idle_expires_at,
        )
    )
    return payload.model_dump(mode="json", exclude_none=True)
