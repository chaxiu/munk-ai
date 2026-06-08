from __future__ import annotations

import re
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from difflib import SequenceMatcher

from munk.perception import ObservationTree, TextDetection

_WHITESPACE_RE = re.compile(r"\s+")

SettleStatus = str
SettleMode = str
SettleDiffFn = Callable[["SettleComparableSnapshot", "SettleComparableSnapshot"], "SettleDiff"]

READY_OCR_CHANGE_THRESHOLD = 0.2
READY_TREE_CHANGE_THRESHOLD = 0.2
STRICT_SETTLE_MODE = "strict"
READY_SETTLE_MODE = "ready"


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
        return None


@dataclass(frozen=True)
class SettleProfile:
    name: SettleMode
    diff_fn: SettleDiffFn
    stable_rounds: int = 1


class GenericSettleStrategy:
    def __init__(
        self,
        *,
        poll_interval_sec: float,
        enhancer: PlatformSettleEnhancer | None = None,
        profile: SettleProfile | None = None,
        diff_fn: SettleDiffFn | None = None,
    ) -> None:
        self._poll_interval_sec = max(0.0, poll_interval_sec)
        self._enhancer = enhancer
        if profile is not None:
            self._profile = profile
        else:
            self._profile = strict_settle_profile(diff_fn=diff_fn)

    @property
    def profile(self) -> SettleProfile:
        return self._profile

    def settle(
        self,
        *,
        before: SettleComparableSnapshot,
        capture: Callable[[], SettleComparableSnapshot],
        timeout_sec: float,
    ) -> SettleResult:
        started = time.monotonic()
        timeout_sec = max(0.0, timeout_sec)
        deadline = started + timeout_sec
        attempts = 0
        baseline_diff = self._diff(before, before)

        now = time.monotonic()
        if now >= deadline and self._poll_interval_sec > 0:
            elapsed_ms = int(round((now - started) * 1000.0))
            return SettleResult(
                status="timeout",
                timed_out=True,
                attempts=attempts,
                elapsed_ms=elapsed_ms,
                final_snapshot=before,
                before_to_final=baseline_diff,
                previous_to_final=None,
                summary=_build_settle_summary("timeout", baseline_diff, None, timed_out=True),
            )

        initial_wait_sec = min(self._poll_interval_sec, max(0.0, deadline - now))
        if initial_wait_sec > 0:
            time.sleep(initial_wait_sec)

        previous = capture()
        attempts += 1
        before_to_previous = self._diff(before, previous)
        changed_seen = before_to_previous.effective_changed
        stable_rounds = 0

        while True:
            now = time.monotonic()
            if now >= deadline:
                status = "changed_but_unstable" if changed_seen else "timeout"
                elapsed_ms = int(round((now - started) * 1000.0))
                return SettleResult(
                    status=status,
                    timed_out=True,
                    attempts=attempts,
                    elapsed_ms=elapsed_ms,
                    final_snapshot=previous,
                    before_to_final=before_to_previous,
                    previous_to_final=None,
                    summary=_build_settle_summary(status, before_to_previous, None, timed_out=True),
                )

            wait_sec = min(self._poll_interval_sec, max(0.0, deadline - now))
            if wait_sec > 0:
                time.sleep(wait_sec)

            current = capture()
            attempts += 1
            previous_to_current = self._diff(previous, current)
            enhanced = None
            if self._enhancer is not None:
                enhanced = self._enhancer.enhance(
                    before=before,
                    previous=previous,
                    current=current,
                )
            if enhanced is not None and enhanced.changed:
                previous_to_current = enhanced
            before_to_current = self._diff(before, current)
            changed_seen = changed_seen or before_to_current.effective_changed

            if not previous_to_current.effective_changed:
                stable_rounds += 1
            else:
                stable_rounds = 0
            if stable_rounds >= self._profile.stable_rounds:
                status = "changed_and_stable" if changed_seen else "no_visible_change"
                elapsed_ms = int(round((time.monotonic() - started) * 1000.0))
                return SettleResult(
                    status=status,
                    timed_out=False,
                    attempts=attempts,
                    elapsed_ms=elapsed_ms,
                    final_snapshot=current,
                    before_to_final=before_to_current,
                    previous_to_final=previous_to_current,
                    summary=_build_settle_summary(status, before_to_current, previous_to_current, timed_out=False),
                )

            previous = current
            before_to_previous = before_to_current

    def _diff(
        self,
        previous: SettleComparableSnapshot,
        current: SettleComparableSnapshot,
    ) -> SettleDiff:
        return self._profile.diff_fn(previous, current)


def build_settle_snapshot(
    *,
    observation_tree: ObservationTree | None,
    texts: list[TextDetection],
    app_state: SettleAppState | None = None,
) -> SettleComparableSnapshot:
    normalized_counts: Counter[str] = Counter()
    normalized_regions: list[tuple[str, tuple[int, int, int, int]]] = []
    for detection in texts:
        normalized_text = _normalize_text(detection.text)
        if not normalized_text:
            continue
        normalized_counts[normalized_text] += 1
        normalized_regions.append((normalized_text, _quantize_box(detection.box)))
    normalized_regions.sort(key=lambda item: (item[0], item[1]))
    return SettleComparableSnapshot(
        tree_signature=_normalize_tree_signature(observation_tree),
        ocr_text_counts=dict(normalized_counts),
        ocr_regions=tuple(normalized_regions),
        app_state=app_state,
    )


def diff_settle_snapshot(
    previous: SettleComparableSnapshot,
    current: SettleComparableSnapshot,
) -> SettleDiff:
    previous_counts = Counter(previous.ocr_text_counts)
    current_counts = Counter(current.ocr_text_counts)
    changed_texts = sorted(set(previous_counts) | set(current_counts))
    appeared: list[tuple[str, int]] = []
    disappeared: list[tuple[str, int]] = []
    for text in changed_texts:
        delta = current_counts.get(text, 0) - previous_counts.get(text, 0)
        if delta > 0:
            appeared.append((text, delta))
        elif delta < 0:
            disappeared.append((text, abs(delta)))
    tree_changed = previous.tree_signature != current.tree_signature
    ocr_changed = previous.ocr_regions != current.ocr_regions
    tree_change_ratio = _compute_tree_change_ratio(previous.tree_signature, current.tree_signature)
    ocr_change_ratio = _compute_ocr_change_ratio(previous_counts, current_counts)
    previous_app_state = previous.app_state or SettleAppState()
    current_app_state = current.app_state or SettleAppState()
    surface_changed = previous_app_state.surface_identity != current_app_state.surface_identity
    load_state_changed = previous_app_state.load_state != current_app_state.load_state
    title_changed = previous_app_state.title != current_app_state.title
    changed = tree_changed or ocr_changed or surface_changed or load_state_changed or title_changed
    return SettleDiff(
        changed=changed,
        effective_changed=changed,
        tree_changed=tree_changed,
        ocr_changed=ocr_changed,
        surface_changed=surface_changed,
        load_state_changed=load_state_changed,
        title_changed=title_changed,
        tree_change_ratio=tree_change_ratio,
        ocr_change_ratio=ocr_change_ratio,
        driver="strict",
        appeared_text_counts=tuple(appeared),
        disappeared_text_counts=tuple(disappeared),
        summary=_build_diff_summary(
            changed=changed,
            effective_changed=changed,
            tree_changed=tree_changed,
            ocr_changed=ocr_changed,
            surface_changed=surface_changed,
            load_state_changed=load_state_changed,
            title_changed=title_changed,
            tree_change_ratio=tree_change_ratio,
            ocr_change_ratio=ocr_change_ratio,
            driver="strict",
            appeared_text_counts=appeared,
            disappeared_text_counts=disappeared,
        ),
    )


def diff_ready_settle_snapshot(
    previous: SettleComparableSnapshot,
    current: SettleComparableSnapshot,
    *,
    ocr_change_threshold: float = READY_OCR_CHANGE_THRESHOLD,
    tree_change_threshold: float = READY_TREE_CHANGE_THRESHOLD,
) -> SettleDiff:
    base = diff_settle_snapshot(previous, current)
    effective_changed = (
        base.ocr_change_ratio > ocr_change_threshold
        or base.tree_change_ratio > tree_change_threshold
    )
    return SettleDiff(
        changed=base.changed,
        effective_changed=effective_changed,
        tree_changed=base.tree_changed,
        ocr_changed=base.ocr_changed,
        surface_changed=base.surface_changed,
        load_state_changed=base.load_state_changed,
        title_changed=base.title_changed,
        tree_change_ratio=base.tree_change_ratio,
        ocr_change_ratio=base.ocr_change_ratio,
        driver="ready",
        appeared_text_counts=base.appeared_text_counts,
        disappeared_text_counts=base.disappeared_text_counts,
        summary=_build_diff_summary(
            changed=base.changed,
            effective_changed=effective_changed,
            tree_changed=base.tree_changed,
            ocr_changed=base.ocr_changed,
            surface_changed=base.surface_changed,
            load_state_changed=base.load_state_changed,
            title_changed=base.title_changed,
            tree_change_ratio=base.tree_change_ratio,
            ocr_change_ratio=base.ocr_change_ratio,
            driver="ready",
            appeared_text_counts=list(base.appeared_text_counts),
            disappeared_text_counts=list(base.disappeared_text_counts),
        ),
    )


def strict_settle_profile(*, diff_fn: SettleDiffFn | None = None) -> SettleProfile:
    return SettleProfile(
        name=STRICT_SETTLE_MODE if diff_fn is None else "custom",
        diff_fn=diff_fn or diff_settle_snapshot,
        stable_rounds=1,
    )


def ready_settle_profile(
    *,
    ocr_change_threshold: float = READY_OCR_CHANGE_THRESHOLD,
    tree_change_threshold: float = READY_TREE_CHANGE_THRESHOLD,
) -> SettleProfile:
    return SettleProfile(
        name=READY_SETTLE_MODE,
        diff_fn=lambda previous, current: diff_ready_settle_snapshot(
            previous,
            current,
            ocr_change_threshold=ocr_change_threshold,
            tree_change_threshold=tree_change_threshold,
        ),
        stable_rounds=2,
    )


def _build_settle_summary(
    status: SettleStatus,
    before_to_final: SettleDiff,
    previous_to_final: SettleDiff | None,
    *,
    timed_out: bool,
) -> str:
    parts = [f"settle={status}"]
    if timed_out:
        parts.append("timed_out=yes")
    parts.append(f"before_diff={before_to_final.summary}")
    if previous_to_final is not None:
        parts.append(f"stability_diff={previous_to_final.summary}")
    return "; ".join(parts)


def _build_diff_summary(
    *,
    changed: bool,
    effective_changed: bool,
    tree_changed: bool,
    ocr_changed: bool,
    surface_changed: bool,
    load_state_changed: bool,
    title_changed: bool,
    tree_change_ratio: float,
    ocr_change_ratio: float,
    driver: str,
    appeared_text_counts: list[tuple[str, int]],
    disappeared_text_counts: list[tuple[str, int]],
) -> str:
    details = [
        f"changed={'yes' if changed else 'no'}",
        f"effective_changed={'yes' if effective_changed else 'no'}",
        f"driver={driver}",
        f"tree_change_ratio={tree_change_ratio:.3f}",
        f"ocr_change_ratio={ocr_change_ratio:.3f}",
    ]
    if tree_changed:
        details.append("tree_changed=yes")
    if ocr_changed:
        details.append("ocr_changed=yes")
    if surface_changed:
        details.append("surface_changed=yes")
    if load_state_changed:
        details.append("load_state_changed=yes")
    if title_changed:
        details.append("title_changed=yes")
    if appeared_text_counts:
        details.append(
            "appeared="
            + ", ".join(f"{text}(+{count})" for text, count in appeared_text_counts[:3])
        )
    if disappeared_text_counts:
        details.append(
            "disappeared="
            + ", ".join(f"{text}(-{count})" for text, count in disappeared_text_counts[:3])
        )
    return "; ".join(details)


def _normalize_tree_signature(observation_tree: ObservationTree | None) -> str | None:
    if observation_tree is None:
        return None
    payload = _WHITESPACE_RE.sub(" ", observation_tree.payload).strip()
    if not payload:
        return f"{observation_tree.source_type}:{observation_tree.content_type}:empty"
    return f"{observation_tree.source_type}:{observation_tree.content_type}:{payload}"


def _normalize_text(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip()


def _compute_tree_change_ratio(previous: str | None, current: str | None) -> float:
    if previous == current:
        return 0.0
    previous_value = previous or ""
    current_value = current or ""
    if not previous_value or not current_value:
        return 1.0
    similarity = SequenceMatcher(None, previous_value, current_value).ratio()
    return max(0.0, min(1.0, 1.0 - similarity))


def _compute_ocr_change_ratio(
    previous_counts: Counter[str],
    current_counts: Counter[str],
) -> float:
    total = sum(previous_counts.values()) + sum(current_counts.values())
    if total <= 0:
        return 0.0
    texts = set(previous_counts) | set(current_counts)
    delta = sum(abs(current_counts.get(text, 0) - previous_counts.get(text, 0)) for text in texts)
    return max(0.0, min(1.0, delta / float(total)))


def _quantize_box(box: tuple[int, int, int, int], *, step: int = 8) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = box
    return (
        int(round(x1 / step) * step),
        int(round(y1 / step) * step),
        int(round(x2 / step) * step),
        int(round(y2 / step) * step),
    )
