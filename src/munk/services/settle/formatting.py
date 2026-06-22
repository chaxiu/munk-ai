from __future__ import annotations

import re

from .models import SettleDiff, SettleStatus

_HAS_TEXT_SIGNAL_RE = re.compile(r"[A-Za-z\u4e00-\u9fff]")
_NUMERIC_NOISE_RE = re.compile(r"^[\d\s:./\\,\-+]+$")
_WHITESPACE_RE = re.compile(r"\s+")


def build_settle_summary(
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


def build_diff_summary(
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
            "appeared=" + ", ".join(f"{text}(+{count})" for text, count in appeared_text_counts[:3])
        )
    if disappeared_text_counts:
        details.append(
            "disappeared=" + ", ".join(f"{text}(-{count})" for text, count in disappeared_text_counts[:3])
        )
    return "; ".join(details)


def _build_settle_change(elapsed_sec: float, diff: SettleDiff) -> str | None:
    if not diff.effective_changed:
        return None
    appeared = _format_settle_change_text(diff.appeared_text_counts, prefix="+", max_items=8)
    disappeared = _format_settle_change_text(diff.disappeared_text_counts, prefix="-", max_items=4)
    if not appeared and not disappeared:
        return None
    parts = [f"t+{elapsed_sec:.1f}s:"]
    if appeared:
        parts.append(appeared)
    if disappeared:
        parts.append(disappeared)
    return " ".join(parts)


def _format_settle_change_text(
    values: tuple[tuple[str, int], ...],
    *,
    prefix: str,
    max_items: int = 8,
) -> str:
    items: list[str] = []
    for text, count in values:
        if _should_filter_settle_change_text(text):
            continue
        items.append(f"{prefix}{text}" if count <= 1 else f"{prefix}{text}({count})")
        if len(items) >= max_items:
            break
    return ",".join(items)


def _should_filter_settle_change_text(text: str) -> bool:
    normalized = _normalize_text(text)
    if not normalized or len(normalized) <= 1:
        return True
    if _NUMERIC_NOISE_RE.fullmatch(normalized):
        return True
    return not _HAS_TEXT_SIGNAL_RE.search(normalized)


def _normalize_text(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip()
