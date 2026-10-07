from __future__ import annotations

from collections import Counter
from difflib import SequenceMatcher

from munk.perception import ObservationTree, TextDetection

from .formatting import _normalize_text, build_diff_summary
from .models import (
    RATIO_SETTLE_MODE,
    READY_OCR_CHANGE_THRESHOLD,
    READY_SETTLE_MODE,
    READY_TREE_CHANGE_THRESHOLD,
    STRICT_SETTLE_MODE,
    SettleAppState,
    SettleComparableSnapshot,
    SettleDiff,
    SettleDiffFn,
    SettleProfile,
)


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
    appeared, disappeared = _compute_text_count_changes(previous_counts, current_counts)
    tree_changed = previous.tree_signature != current.tree_signature
    ocr_changed = previous.ocr_regions != current.ocr_regions
    tree_change_ratio = _compute_tree_change_ratio(previous.tree_signature, current.tree_signature)
    ocr_change_ratio = _compute_ocr_change_ratio(previous_counts, current_counts)
    surface_changed, load_state_changed, title_changed = _compute_app_state_changes(
        previous.app_state,
        current.app_state,
    )
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
        driver=STRICT_SETTLE_MODE,
        appeared_text_counts=tuple(appeared),
        disappeared_text_counts=tuple(disappeared),
        summary=build_diff_summary(
            changed=changed,
            effective_changed=changed,
            tree_changed=tree_changed,
            ocr_changed=ocr_changed,
            surface_changed=surface_changed,
            load_state_changed=load_state_changed,
            title_changed=title_changed,
            tree_change_ratio=tree_change_ratio,
            ocr_change_ratio=ocr_change_ratio,
            driver=STRICT_SETTLE_MODE,
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
    driver: str = READY_SETTLE_MODE,
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
        driver=driver,
        appeared_text_counts=base.appeared_text_counts,
        disappeared_text_counts=base.disappeared_text_counts,
        summary=build_diff_summary(
            changed=base.changed,
            effective_changed=effective_changed,
            tree_changed=base.tree_changed,
            ocr_changed=base.ocr_changed,
            surface_changed=base.surface_changed,
            load_state_changed=base.load_state_changed,
            title_changed=base.title_changed,
            tree_change_ratio=base.tree_change_ratio,
            ocr_change_ratio=base.ocr_change_ratio,
            driver=driver,
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


def ratio_settle_profile(
    *,
    change_threshold: float = READY_OCR_CHANGE_THRESHOLD,
) -> SettleProfile:
    threshold = max(0.0, min(1.0, change_threshold))
    return SettleProfile(
        name=RATIO_SETTLE_MODE,
        diff_fn=lambda previous, current: diff_ready_settle_snapshot(
            previous,
            current,
            ocr_change_threshold=threshold,
            tree_change_threshold=threshold,
            driver=RATIO_SETTLE_MODE,
        ),
        stable_rounds=2,
    )


def _normalize_tree_signature(observation_tree: ObservationTree | None) -> str | None:
    if observation_tree is None:
        return None
    payload = _normalize_text(observation_tree.payload)
    if not payload:
        return f"{observation_tree.source_type}:{observation_tree.content_type}:empty"
    return f"{observation_tree.source_type}:{observation_tree.content_type}:{payload}"


def _compute_text_count_changes(
    previous_counts: Counter[str],
    current_counts: Counter[str],
) -> tuple[list[tuple[str, int]], list[tuple[str, int]]]:
    appeared: list[tuple[str, int]] = []
    disappeared: list[tuple[str, int]] = []
    for text in sorted(set(previous_counts) | set(current_counts)):
        delta = current_counts.get(text, 0) - previous_counts.get(text, 0)
        if delta > 0:
            appeared.append((text, delta))
        elif delta < 0:
            disappeared.append((text, abs(delta)))
    return appeared, disappeared


def _compute_app_state_changes(
    previous_app_state: SettleAppState | None,
    current_app_state: SettleAppState | None,
) -> tuple[bool, bool, bool]:
    previous_value = previous_app_state or SettleAppState()
    current_value = current_app_state or SettleAppState()
    return (
        previous_value.surface_identity != current_value.surface_identity,
        previous_value.load_state != current_value.load_state,
        previous_value.title != current_value.title,
    )


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
