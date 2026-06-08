from __future__ import annotations

import logging
import time

from munk.config.resolve import resolve_runtime_config
from munk.services.settle import (
    GenericSettleStrategy,
    SettleComparableSnapshot,
    SettleDiff,
    SettleProfile,
    SettleResult,
    build_settle_snapshot,
    diff_settle_snapshot,
)

from .helpers import _capture_observation_tree
from .session_context import InteractiveSessionContext

_logger = logging.getLogger(__name__)


def capture_interactive_settle_snapshot(
    *,
    context: InteractiveSessionContext,
) -> SettleComparableSnapshot:
    started = time.monotonic()
    stage_started = started
    screen_bgr = context.device.screenshot_bgr()
    screenshot_ms = int(round((time.monotonic() - stage_started) * 1000.0))

    stage_started = time.monotonic()
    observation_tree = _capture_observation_tree(context)
    tree_ms = int(round((time.monotonic() - stage_started) * 1000.0))

    stage_started = time.monotonic()
    texts = context.perception.analyze_text(screen_bgr)
    ocr_ms = int(round((time.monotonic() - stage_started) * 1000.0))

    snapshot = build_settle_snapshot(
        observation_tree=observation_tree,
        texts=texts,
    )
    total_ms = int(round((time.monotonic() - started) * 1000.0))
    _logger.info(
        "interactive_settle_capture total_ms=%s screenshot_ms=%s tree_ms=%s ocr_ms=%s "
        "tree_present=%s text_count=%s",
        total_ms,
        screenshot_ms,
        tree_ms,
        ocr_ms,
        observation_tree is not None,
        len(texts),
    )
    return snapshot


def settle_interactive_after_action(
    *,
    context: InteractiveSessionContext,
    before: SettleComparableSnapshot,
    settle_timeout_sec: float | None = None,
) -> SettleResult:
    runtime = resolve_runtime_config(context.resolved_config.config)
    poll_interval_sec = context.settle_poll_interval_sec or runtime.interval
    strategy = GenericSettleStrategy(
        poll_interval_sec=poll_interval_sec,
        profile=interactive_settle_profile(),
    )
    timeout_sec = context.settle_timeout_sec if settle_timeout_sec is None else max(0.0, settle_timeout_sec)
    _logger.info(
        "interactive_settle_start timeout_sec=%s poll_interval_sec=%s before_tree_present=%s before_text_count=%s",
        timeout_sec,
        poll_interval_sec,
        before.tree_signature is not None,
        sum(before.ocr_text_counts.values()),
    )
    result = strategy.settle(
        before=before,
        capture=lambda: capture_interactive_settle_snapshot(context=context),
        timeout_sec=timeout_sec,
    )
    _logger.info(
        "interactive_settle_result status=%s timed_out=%s attempts=%s elapsed_ms=%s summary=%s",
        result.status,
        result.timed_out,
        result.attempts,
        result.elapsed_ms,
        result.summary,
    )
    return result


def diff_interactive_settle_snapshot(
    previous: SettleComparableSnapshot,
    current: SettleComparableSnapshot,
) -> SettleDiff:
    base = diff_settle_snapshot(previous, current)
    previous_has_ocr = _has_ocr_signal(previous)
    current_has_ocr = _has_ocr_signal(current)
    if previous_has_ocr or current_has_ocr:
        driver = "ocr"
        changed = base.ocr_changed
    else:
        driver = "tree_fallback"
        changed = base.tree_changed
    return SettleDiff(
        changed=changed,
        effective_changed=changed,
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
        summary=_build_interactive_diff_summary(
            changed=changed,
            driver=driver,
            base=base,
        ),
    )


def interactive_settle_profile() -> SettleProfile:
    return SettleProfile(
        name="interactive",
        diff_fn=diff_interactive_settle_snapshot,
        stable_rounds=1,
    )


def _has_ocr_signal(snapshot: SettleComparableSnapshot) -> bool:
    return bool(snapshot.ocr_regions) and bool(snapshot.ocr_text_counts)


def _build_interactive_diff_summary(
    *,
    changed: bool,
    driver: str,
    base: SettleDiff,
) -> str:
    parts = [f"changed={'yes' if changed else 'no'}", f"driver={driver}"]
    if base.tree_changed:
        parts.append("tree_changed=yes")
    if base.ocr_changed:
        parts.append("ocr_changed=yes")
    if base.appeared_text_counts:
        parts.append(
            "appeared="
            + ", ".join(f"{text}(+{count})" for text, count in base.appeared_text_counts[:3])
        )
    if base.disappeared_text_counts:
        parts.append(
            "disappeared="
            + ", ".join(f"{text}(-{count})" for text, count in base.disappeared_text_counts[:3])
        )
    return "; ".join(parts)
