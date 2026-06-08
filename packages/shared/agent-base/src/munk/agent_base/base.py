from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Literal, TypeAlias

from munk.perception import ObservationTree
from munk.perception.image import BgrImage
from munk.perception.types import ClickableElement

from .types import Action

if TYPE_CHECKING:
    from munk.core.screen_graph import ObservedScreenFrame, ScreenDiff


@dataclass(frozen=True)
class ActionObservation:
    screen_changed: bool
    appeared_texts: list[str]
    disappeared_texts: list[str]
    appeared_text_counts: list[tuple[str, int]]
    disappeared_text_counts: list[tuple[str, int]]
    previous_text_snapshot: list[str]
    current_text_snapshot: list[str]
    summary: str
    screen_diff: ScreenDiff | None = None


ActionFeedbackValue: TypeAlias = (
    str
    | int
    | float
    | bool
    | None
    | tuple[int, int]
    | tuple[int, int, int, int]
    | list[object]
    | dict[str, object]
)


@dataclass(frozen=True)
class ActionFeedback:
    action_type: str
    status: Literal["executed", "failed"] = "executed"
    fields: tuple[tuple[str, ActionFeedbackValue], ...] = ()


@dataclass(frozen=True)
class ActionHistoryEntry:
    action_type: str
    target_id: int | None
    target_label: str | None
    summary: str
    detail: str | None = None
    outcome_summary: str | None = None
    memory_operation: str | None = None
    memory_key: str | None = None
    memory_summary: str | None = None

    def to_compact_dict(self) -> dict[str, object]:
        payload = asdict(self)
        if self.target_id is None:
            payload.pop("target_id", None)
        if self.target_label is None:
            payload.pop("target_label", None)
        if self.detail is None:
            payload.pop("detail", None)
        if self.outcome_summary is None:
            payload.pop("outcome_summary", None)
        if self.memory_operation is None:
            payload.pop("memory_operation", None)
        if self.memory_key is None:
            payload.pop("memory_key", None)
        if self.memory_summary is None:
            payload.pop("memory_summary", None)
        return payload


@dataclass(frozen=True)
class ScreenState:
    elements: list[ClickableElement]
    screen_size: tuple[int, int]
    entry_identity: str | None
    image_bgr: BgrImage | None = None
    last_action_observation: ActionObservation | None = None
    last_action_feedback: ActionFeedback | None = None
    screen_frame: ObservedScreenFrame | None = None
    platform: str | None = None
    platform_context: dict[str, object] | None = None
    surface_identity: str | None = None


ObservationSnapshotSource = Literal[
    "step_pre_action",
    "post_action_retry",
    "post_action_final",
]


@dataclass(frozen=True)
class RuntimeObservationSnapshot:
    screen: ScreenState
    observation_tree: ObservationTree | None
    icon_conf: float
    source: ObservationSnapshotSource


class Brain(ABC):
    @abstractmethod
    def next_action(self, screen: ScreenState) -> Action:
        raise NotImplementedError

    def on_step_started(self, step_index: int) -> None:
        return None
