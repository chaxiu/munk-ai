from __future__ import annotations

from typing import Any, cast

from pydantic import BaseModel

from munk.recording import (
    ForwardingAck,
    ForwardingEvent,
    ForwardingStep,
    ObservedTapCommand,
    ObservationSnapshot,
    PointerForwardingPayload,
    PointerStepPayload,
    RecordedInputEvent,
    RecordInteractionCommand,
)
from munk.recording.models import now_iso


def tap_to_interaction(command: ObservedTapCommand) -> RecordInteractionCommand:
    x_ratio = command.x_ratio if command.x_ratio is not None else round(command.x / command.width, 6)
    y_ratio = command.y_ratio if command.y_ratio is not None else round(command.y / command.height, 6)
    pointer_payload = PointerForwardingPayload(
        pointer_id=0,
        start_x=command.x,
        start_y=command.y,
        end_x=command.x,
        end_y=command.y,
        width=command.width,
        height=command.height,
    )
    steps = [
        ForwardingStep(
            seq=1,
            step_kind="pointer_down",
            payload=PointerStepPayload(pointer_id=0, x=command.x, y=command.y),
        ),
        ForwardingStep(
            seq=2,
            step_kind="pointer_up",
            payload=PointerStepPayload(pointer_id=0, x=command.x, y=command.y),
        ),
    ]
    return RecordInteractionCommand(
        client_command_id=f"tap-{command.x}-{command.y}",
        kind="click",
        forwarding_ack=ForwardingAck(
            kind="pointer",
            dispatched_at=now_iso(),
            payload=pointer_payload,
            steps=steps,
        ),
        payload={
            "x": command.x,
            "y": command.y,
            "width": command.width,
            "height": command.height,
            "x_ratio": x_ratio,
            "y_ratio": y_ratio,
        },
        source=command.source,
    )


def build_forwarding_event(
    *,
    recording_id: str,
    command: RecordInteractionCommand,
    next_index: int,
) -> ForwardingEvent:
    return ForwardingEvent(
        forwarding_event_id=f"fwd_{next_index:06d}",
        recording_id=recording_id,
        client_command_id=command.client_command_id,
        kind=command.forwarding_ack.kind,
        dispatched_at=command.forwarding_ack.dispatched_at,
        ack_at=command.forwarding_ack.ack_at,
        payload=command.forwarding_ack.payload,
        steps=command.forwarding_ack.steps,
        device_result=command.forwarding_ack.device_result,
    )


def build_recording_event(
    *,
    recording_id: str,
    command: RecordInteractionCommand,
    after_observation: ObservationSnapshot,
    next_index: int,
) -> RecordedInputEvent:
    return RecordedInputEvent(
        event_id=f"evt_{next_index:06d}",
        recording_id=recording_id,
        kind=command.kind,
        summary=build_summary(command),
        source=command.source,
        payload={
            **command.payload,
            "client_command_id": command.client_command_id,
            "after_observation_id": after_observation.observation_id,
            "entry_identity": after_observation.entry_identity,
            "surface_identity": after_observation.surface_identity,
        },
    )


def build_summary(command: RecordInteractionCommand) -> str:
    payload = _payload_to_dict(command.payload) if command.payload else _payload_to_dict(command.forwarding_ack.payload)
    if command.kind == "click":
        return f"click at ({payload.get('x')}, {payload.get('y')})"
    if command.kind == "swipe":
        return (
            f"swipe from ({payload.get('start_x')}, {payload.get('start_y')}) "
            f"to ({payload.get('end_x')}, {payload.get('end_y')})"
        )
    if command.kind == "input":
        return f"input text: {payload.get('text', '')}"
    return "press back"


def _payload_to_dict(payload_obj: dict[str, Any] | BaseModel) -> dict[str, Any]:
    if isinstance(payload_obj, BaseModel):
        return cast(dict[str, Any], payload_obj.model_dump(mode="json"))
    return cast(dict[str, Any], payload_obj)
