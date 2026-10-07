from __future__ import annotations

from typing import Any, Callable, Protocol

from pydantic import BaseModel, ConfigDict
from munk.agent_base.llm import extract_transcript_entry_text
from munk.agent_base.llm.transcript import LlmResponseTranscriptEntry, LlmTranscriptEntry

_SUMMARY_MAX_CHARS = 240


class LlmRequestTimelinePayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    llm_request_id: str | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_text: str | None = None


class LlmResponseTimelinePayload(LlmRequestTimelinePayload):
    llm_status_code: int | None = None


class LlmTimelineTracker(Protocol):
    def append_timeline_event(
        self,
        *,
        event_type: str,
        message: str | None,
        agent_role: str,
        timeline_scope: str,
        timeline_phase: str,
        summary: str | None = None,
        attempt_index: int | None = None,
        timestamp: str | None = None,
        parent_operation_id: str | None = None,
        child_operation_id: str | None = None,
        app_id: str | None = None,
        plan_id: str | None = None,
        case_id: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> None: ...


def build_llm_timeline_observer(
    *,
    tracker: LlmTimelineTracker,
    agent_role: str,
    attempt_index: int | None,
    app_id: str | None,
    plan_id: str,
    case_id: str,
    timeline_scope: str = "parent_run",
    parent_operation_id: str | None = None,
    child_operation_id: str | None = None,
) -> Callable[[LlmTranscriptEntry], None]:
    def observer(entry: LlmTranscriptEntry) -> None:
        payload = _build_llm_event_payload(entry)
        is_request = entry.kind == "llm_request"
        tracker.append_timeline_event(
            event_type=entry.kind,
            message=f"{agent_role} llm {'request' if is_request else 'response'}",
            agent_role=agent_role,
            timeline_scope=timeline_scope,
            timeline_phase="submitted" if is_request else "result_ready",
            summary=_summarize_text(payload.get("llm_text")),
            attempt_index=attempt_index,
            parent_operation_id=parent_operation_id,
            child_operation_id=child_operation_id,
            app_id=app_id,
            plan_id=plan_id,
            case_id=case_id,
            data=payload,
        )

    return observer


def _build_llm_event_payload(entry: LlmTranscriptEntry) -> dict[str, Any]:
    text = extract_transcript_entry_text(entry)
    if isinstance(entry, LlmResponseTranscriptEntry):
        payload = LlmResponseTimelinePayload(
            llm_request_id=entry.request_id,
            llm_status_code=entry.status_code,
            llm_provider=entry.provider,
            llm_model=entry.model,
            llm_text=text,
        )
    else:
        payload = LlmRequestTimelinePayload(
            llm_request_id=entry.request_id,
            llm_provider=entry.provider,
            llm_model=entry.model,
            llm_text=text,
        )
    return payload.model_dump(mode="json", exclude_none=True)


def _summarize_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.split())
    if not normalized:
        return None
    if len(normalized) <= _SUMMARY_MAX_CHARS:
        return normalized
    return normalized[: _SUMMARY_MAX_CHARS - 1].rstrip() + "…"
