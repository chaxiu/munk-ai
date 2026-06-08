from __future__ import annotations

from typing import Any

from munk.adapters.mcp.tool_outputs import SubmittedOperationOutput
from munk.services.machine_contracts import MachineCommandResponse


def submitted_operation_output(response: MachineCommandResponse, *, action_label: str) -> SubmittedOperationOutput:
    payload = response.payload
    if payload.get("ok") is not True:
        error = payload.get("error") or {}
        message = error.get("message") if isinstance(error, dict) else None
        raise RuntimeError(str(message or f"{action_label} failed"))

    data = payload.get("data")
    if not isinstance(data, dict):
        raise RuntimeError(f"{action_label} returned invalid machine payload")

    operation_id = _string_or_none(data.get("operation_id"))
    status = _string_or_none(data.get("status"))
    if operation_id is None or status is None:
        raise RuntimeError(f"{action_label} result is missing operation_id or status")

    phase = _string_or_none(data.get("phase"))
    app_id = _string_or_none(data.get("app_id"))
    plan_id = _string_or_none(data.get("plan_id"))
    verification_verdict = _string_or_none(data.get("verification_verdict"))
    summary_bits = [f"{action_label} submitted", f"operation_id={operation_id}", f"status={status}"]
    if phase:
        summary_bits.append(f"phase={phase}")
    if plan_id:
        summary_bits.append(f"plan_id={plan_id}")
    return SubmittedOperationOutput(
        summary=", ".join(summary_bits),
        operation_id=operation_id,
        status=status,
        phase=phase,
        app_id=app_id,
        plan_id=plan_id,
        verification_verdict=verification_verdict,
    )


def require_success_payload(response: MachineCommandResponse, *, action_label: str) -> dict[str, Any]:
    payload = response.payload
    if payload.get("ok") is not True:
        error = payload.get("error") or {}
        message = error.get("message") if isinstance(error, dict) else None
        raise RuntimeError(str(message or f"{action_label} failed"))
    data = payload.get("data")
    if not isinstance(data, dict):
        raise RuntimeError(f"{action_label} returned invalid machine payload")
    return data


def _string_or_none(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None
