from __future__ import annotations

from dataclasses import dataclass

from munk.agent_base.action import Action
from munk.core.action_target_refs import normalize_target_ref

from munk_runner_local.target_handle_fingerprint import handle_fingerprint

POSTCHECK_FAILURE_WARNING_CODE = "same_target_postcheck_failure"
POSTCHECK_FAILURE_THRESHOLD_ERROR = "same_target_postcheck_failure_threshold_exceeded"
POSTCHECK_FAILURE_WARN_AT = 2
POSTCHECK_FAILURE_STOP_AT = 3


@dataclass(frozen=True)
class PostcheckFailureTrackingState:
    identity: str | None = None
    count: int = 0
    last_summary: str | None = None


def resolve_postcheck_identity(action: Action) -> str | None:
    fingerprint = handle_fingerprint(action.handle)
    if fingerprint is not None:
        return "handle:" + ":".join(fingerprint)
    raw_ref = str(action.target_ref or "").strip()
    if raw_ref:
        try:
            return f"ref:{normalize_target_ref(raw_ref)}"
        except ValueError:
            return f"ref:{raw_ref.lower()}"
    return None


def update_postcheck_failure_state(
    state: PostcheckFailureTrackingState,
    *,
    action: Action,
    postcheck_passed: bool | None,
    postcheck_summary: str | None,
) -> PostcheckFailureTrackingState:
    if postcheck_passed is None:
        return state
    if postcheck_passed:
        return PostcheckFailureTrackingState()
    identity = resolve_postcheck_identity(action)
    if identity is None:
        return PostcheckFailureTrackingState()
    summary = str(postcheck_summary or "").strip() or None
    if state.identity == identity:
        return PostcheckFailureTrackingState(
            identity=identity,
            count=state.count + 1,
            last_summary=summary,
        )
    return PostcheckFailureTrackingState(identity=identity, count=1, last_summary=summary)


def build_postcheck_failure_advice(identity: str | None) -> str:
    ref_hint = ""
    if identity is not None and identity.startswith("handle:"):
        ref_hint = " Confirm the structure target (#t*) and value, or skip optional fields."
    elif identity is not None and identity.startswith("ref:v"):
        ref_hint = " Prefer a #t* structure target for native form controls."
    elif identity is not None and identity.startswith("ref:t"):
        ref_hint = " Confirm the #t* target and value, or skip optional fields."
    return (
        "Change strategy: switch target channel (#t*), skip optional fields, or stop."
        f"{ref_hint}"
    )


def should_warn_for_postcheck_failures(state: PostcheckFailureTrackingState) -> bool:
    return state.count >= POSTCHECK_FAILURE_WARN_AT and state.identity is not None


def should_stop_for_postcheck_failures(state: PostcheckFailureTrackingState) -> bool:
    return state.count >= POSTCHECK_FAILURE_STOP_AT and state.identity is not None
