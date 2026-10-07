from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

SettleStatus = str
SettleMode = str
SettleDiffFn = Callable[["SettleComparableSnapshot", "SettleComparableSnapshot"], "SettleDiff"]

READY_OCR_CHANGE_THRESHOLD = 0.2
READY_TREE_CHANGE_THRESHOLD = 0.2
STRICT_SETTLE_MODE = "strict"
RATIO_SETTLE_MODE = "ratio"
READY_SETTLE_MODE = "ready"
DELAY_SETTLE_MODE = "delay"


@dataclass(frozen=True)
class SettleAppState:
    surface_identity: str | None = None
    load_state: str | None = None
    title: str | None = None


@dataclass(frozen=True)
class SettleComparableSnapshot:
    tree_signature: str | None
    ocr_text_counts: dict[str, int]
    ocr_regions: tuple[tuple[str, tuple[int, int, int, int]], ...]
    app_state: SettleAppState | None = None


@dataclass(frozen=True)
class SettleDiff:
    changed: bool
    effective_changed: bool
    tree_changed: bool
    ocr_changed: bool
    surface_changed: bool
    load_state_changed: bool
    title_changed: bool
    tree_change_ratio: float
    ocr_change_ratio: float
    driver: str
    appeared_text_counts: tuple[tuple[str, int], ...]
    disappeared_text_counts: tuple[tuple[str, int], ...]
    summary: str


@dataclass(frozen=True)
class SettleResult:
    status: SettleStatus
    timed_out: bool
    attempts: int
    elapsed_ms: int
    final_snapshot: SettleComparableSnapshot
    before_to_final: SettleDiff
    previous_to_final: SettleDiff | None
    summary: str
    changes: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlatformSettleEnhancer:
    name: str

    def enhance(
        self,
        *,
        before: SettleComparableSnapshot,
        previous: SettleComparableSnapshot,
        current: SettleComparableSnapshot,
    ) -> SettleDiff | None:
        _ = before, previous, current
        return None


@dataclass(frozen=True)
class SettleProfile:
    name: SettleMode
    diff_fn: SettleDiffFn
    stable_rounds: int = 1
