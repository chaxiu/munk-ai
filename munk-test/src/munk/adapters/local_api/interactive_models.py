from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from munk.app import AppTarget
from munk.services.errors import DeviceConflictError
from munk.services.interactive.models import InteractiveFinalizeResult, InteractiveSession

InteractiveSessionStatusLiteral = Literal[
    "created",
    "waiting_agent",
    "acting",
    "finalized",
    "aborted",
    "expired",
]


class CreateInteractiveSessionRequest(BaseModel):
    app_target: AppTarget = Field(description="Application target to bind the interactive session to.")
    device_ref: str | None = Field(
        default=None,
        description="Optional device reference to claim for the interactive session.",
    )
    config_path: str | None = Field(
        default=None,
        description="Optional path to a Munk config file; otherwise workspace/profile discovery applies.",
    )


class FinalizeInteractiveSessionRequest(BaseModel):
    summary: str | None = Field(
        default=None,
        description="Optional agent or host summary recorded on finalize.",
    )


class InteractiveSessionPayload(BaseModel):
    session_id: str = Field(description="Interactive session identifier.")
    status: InteractiveSessionStatusLiteral = Field(description="Current interactive session status.")
    platform: str = Field(description="Interactive target platform.")
    app_id: str = Field(description="Application identifier associated with the session.")
    device_ref: str | None = Field(default=None, description="Claimed device reference when available.")
    step_count: int = Field(description="Current recorded step count.")
    started_at: str = Field(description="Session start timestamp in ISO format.")
    updated_at: str = Field(description="Session update timestamp in ISO format.")
    last_active_at: str = Field(description="Last agent activity timestamp in ISO format.")
    expires_at: str = Field(description="Session absolute expiry timestamp in ISO format.")
    idle_expires_at: str = Field(description="Session idle expiry timestamp in ISO format.")
    last_observation_summary: str | None = Field(
        default=None,
        description="Summary of the latest observation when available.",
    )
    finalized_agent_summary: str | None = Field(
        default=None,
        description="Agent summary from finalize when available.",
    )


class InteractiveSessionCreateData(BaseModel):
    session: InteractiveSessionPayload


class InteractiveSessionGetData(BaseModel):
    session: InteractiveSessionPayload


class InteractiveSessionAbortData(BaseModel):
    session: InteractiveSessionPayload


class InteractiveSessionFinalizeData(BaseModel):
    session: InteractiveSessionPayload
    step_count: int = Field(description="Recorded step count at finalize time.")
    steps_summary: list[str] = Field(default_factory=list, description="Transcript of step summaries.")
    last_observation_summary: str | None = Field(
        default=None,
        description="Summary of the latest observation when available.",
    )
    agent_summary: str | None = Field(default=None, description="Optional summary provided at finalize.")


def project_interactive_session(session: InteractiveSession) -> InteractiveSessionPayload:
    """Project InteractiveSession into a Host-facing Local API payload."""
    return InteractiveSessionPayload(
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
            session.finalized_result.agent_summary if session.finalized_result is not None else None
        ),
    )


def build_interactive_device_conflict_details(exc: DeviceConflictError) -> dict[str, Any]:
    """Build Local API conflict details with Host-oriented recovery guidance."""
    can_resume = exc.blocking_kind == "interactive_session"
    resume_session_id = exc.blocking_operation_id if can_resume else None
    if can_resume:
        suggested_next_actions = [
            f"GET /v1/interactive/sessions/{resume_session_id}",
            f"POST /v1/interactive/sessions/{resume_session_id}/finalize",
            f"POST /v1/interactive/sessions/{resume_session_id}/abort",
        ]
    else:
        suggested_next_actions = [
            "GET /v1/devices",
            "POST /v1/interactive/sessions with another device_ref",
            "wait for the blocking operation to finish",
        ]
    details: dict[str, Any] = {
        **exc.to_details(),
        "blocked_by": exc.blocking_operation_id,
        "can_resume": can_resume,
        "resume_session_id": resume_session_id,
        "suggested_next_actions": suggested_next_actions,
    }
    return details


def project_finalize_data(
    *,
    session: InteractiveSession,
    result: InteractiveFinalizeResult,
) -> InteractiveSessionFinalizeData:
    return InteractiveSessionFinalizeData(
        session=project_interactive_session(session),
        step_count=result.step_count,
        steps_summary=list(result.steps_summary),
        last_observation_summary=result.last_observation_summary,
        agent_summary=result.agent_summary,
    )
