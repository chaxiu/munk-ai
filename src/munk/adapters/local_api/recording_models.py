from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from munk.app import AppTarget
from munk.recording import (
    ForwardingAck,
    ForwardingStep,
    ObservedTapCommand,
    RecordingInteractionKind,
    RecordInteractionCommand,
    validate_record_interaction_contract,
)


class CreateRecordingRequest(BaseModel):
    app_target: AppTarget
    device_ref: str | None = None
    case_id: str | None = None


class ObserveTapRequest(BaseModel):
    x: int
    y: int
    width: int
    height: int
    x_ratio: float | None = None
    y_ratio: float | None = None
    source: str = "scrcpy_bridge"

    def to_command(self) -> ObservedTapCommand:
        return ObservedTapCommand(
            x=self.x,
            y=self.y,
            width=self.width,
            height=self.height,
            x_ratio=self.x_ratio,
            y_ratio=self.y_ratio,
            source=self.source,
        )


class ForwardingStepRequest(ForwardingStep):
    pass

    def to_model(self) -> ForwardingStep:
        return ForwardingStep.model_validate(self.model_dump(exclude_none=True))


class ForwardingAckRequest(ForwardingAck):
    steps: list[ForwardingStepRequest] = Field(default_factory=list)

    def to_model(self) -> ForwardingAck:
        return ForwardingAck.model_validate(self.model_dump(exclude_none=True))


class RecordInteractionRequest(BaseModel):
    client_command_id: str
    kind: RecordingInteractionKind
    forwarding_ack: ForwardingAckRequest
    payload: dict[str, Any] = Field(default_factory=dict)
    source: str = "scrcpy_bridge"

    def to_command(self) -> RecordInteractionCommand:
        command = RecordInteractionCommand(
            client_command_id=self.client_command_id,
            kind=self.kind,
            forwarding_ack=self.forwarding_ack.to_model(),
            payload=self.payload,
            source=self.source,
        )
        validate_record_interaction_contract(command)
        return command
