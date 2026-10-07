from __future__ import annotations

from collections import Counter

from munk.agent_base.base import ActionObservation, ScreenState
from munk.core.screen_graph import ObservedNodeChange, ObservedScreenFrame, ScreenDiff


def extract_screen_texts(screen: ScreenState) -> list[str]:
    texts: list[str] = []
    for element in screen.elements:
        text = element.text.strip()
        if not text:
            continue
        texts.append(text)
    return texts


def count_screen_texts(texts: list[str]) -> dict[str, int]:
    return dict(Counter(texts))


def build_observation_summary(
    changed: bool,
    appeared_text_counts: list[tuple[str, int]],
    disappeared_text_counts: list[tuple[str, int]],
) -> str:
    if not changed:
        return "screen_changed=no"
    details: list[str] = []
    if appeared_text_counts:
        appeared = ", ".join(f"{text}(+{count})" for text, count in appeared_text_counts[:3])
        details.append(f"appeared={appeared}")
    if disappeared_text_counts:
        disappeared = ", ".join(f"{text}(-{count})" for text, count in disappeared_text_counts[:3])
        details.append(f"disappeared={disappeared}")
    if not details:
        return "screen_changed=yes"
    return f"screen_changed=yes; {'; '.join(details)}"


def build_screen_diff(
    previous_frame: ObservedScreenFrame,
    current_frame: ObservedScreenFrame,
) -> ScreenDiff:
    previous_by_key = {node.stable_key: node for node in previous_frame.tree_nodes}
    current_by_key = {node.stable_key: node for node in current_frame.tree_nodes}
    appeared: list[ObservedNodeChange] = []
    disappeared: list[ObservedNodeChange] = []
    updated: list[ObservedNodeChange] = []

    for stable_key, node in current_by_key.items():
        previous = previous_by_key.get(stable_key)
        if previous is None:
            appeared.append(
                ObservedNodeChange(
                    change_type="appeared",
                    stable_key=node.stable_key,
                    label=node.label(),
                )
            )
            continue
        changes = _node_change_parts(previous, node)
        if changes:
            updated.append(
                ObservedNodeChange(
                    change_type="updated",
                    stable_key=node.stable_key,
                    label=node.label(),
                )
            )

    for stable_key, node in previous_by_key.items():
        if stable_key in current_by_key:
            continue
        disappeared.append(
            ObservedNodeChange(
                change_type="disappeared",
                stable_key=node.stable_key,
                label=node.label(),
            )
        )

    changed = bool(appeared or disappeared or updated)
    business_appeared = _prioritize_business_changes(appeared, current_frame.entry_identity)
    business_disappeared = _prioritize_business_changes(disappeared, previous_frame.entry_identity)
    business_updated = _prioritize_business_changes(
        updated,
        current_frame.entry_identity or previous_frame.entry_identity,
    )
    business_changed = bool(business_appeared or business_disappeared or business_updated)
    return ScreenDiff(
        changed=business_changed if changed else False,
        summary=_build_screen_diff_summary(
            business_changed if changed else False,
            business_appeared,
            business_disappeared,
            business_updated,
        ),
        appeared_nodes=appeared,
        disappeared_nodes=disappeared,
        updated_nodes=updated,
        linked_visual_changes=_linked_visual_change_summary(
            business_appeared,
            business_disappeared,
            business_updated,
        ),
    )


def observe_action_result(
    previous_screen: ScreenState,
    current_screen: ScreenState,
) -> ActionObservation:
    previous_texts = extract_screen_texts(previous_screen)
    current_texts = extract_screen_texts(current_screen)
    previous_counts = count_screen_texts(previous_texts)
    current_counts = count_screen_texts(current_texts)
    changed_texts = sorted(set(previous_counts) | set(current_counts))
    appeared_text_counts: list[tuple[str, int]] = []
    disappeared_text_counts: list[tuple[str, int]] = []
    for text in changed_texts:
        delta = current_counts.get(text, 0) - previous_counts.get(text, 0)
        if delta > 0:
            appeared_text_counts.append((text, delta))
        elif delta < 0:
            disappeared_text_counts.append((text, abs(delta)))
    appeared_texts = [text for text, _ in appeared_text_counts]
    disappeared_texts = [text for text, _ in disappeared_text_counts]
    screen_diff: ScreenDiff | None = None
    if (
        previous_screen.screen_frame is not None
        and current_screen.screen_frame is not None
        and previous_screen.screen_frame.tree_available
        and current_screen.screen_frame.tree_available
        and (previous_screen.screen_frame.tree_nodes or current_screen.screen_frame.tree_nodes)
    ):
        screen_diff = build_screen_diff(previous_screen.screen_frame, current_screen.screen_frame)
    screen_changed = screen_diff.changed if screen_diff is not None else bool(appeared_text_counts or disappeared_text_counts)
    summary = (
        screen_diff.summary
        if screen_diff is not None
        else build_observation_summary(
            changed=screen_changed,
            appeared_text_counts=appeared_text_counts,
            disappeared_text_counts=disappeared_text_counts,
        )
    )
    return ActionObservation(
        screen_changed=screen_changed,
        appeared_texts=appeared_texts,
        disappeared_texts=disappeared_texts,
        appeared_text_counts=appeared_text_counts,
        disappeared_text_counts=disappeared_text_counts,
        previous_text_snapshot=previous_texts,
        current_text_snapshot=current_texts,
        summary=summary,
        screen_diff=screen_diff,
    )


def _node_change_parts(previous: object, current: object) -> list[str]:
    prev = previous
    curr = current
    parts: list[str] = []
    for field_name in ("text", "content_desc", "enabled", "checked", "selected", "focused", "bounds"):
        if getattr(prev, field_name) != getattr(curr, field_name):
            parts.append(field_name)
    return parts


def _build_screen_diff_summary(
    changed: bool,
    appeared: list[ObservedNodeChange],
    disappeared: list[ObservedNodeChange],
    updated: list[ObservedNodeChange],
) -> str:
    if not changed:
        return "screen_changed=no"
    details: list[str] = []
    if appeared:
        labels = ", ".join(change.label for change in appeared[:2])
        details.append(f"appeared_nodes={labels}")
    if disappeared:
        labels = ", ".join(change.label for change in disappeared[:2])
        details.append(f"disappeared_nodes={labels}")
    if updated:
        labels = ", ".join(change.label for change in updated[:2])
        details.append(f"updated_nodes={labels}")
    if not details:
        return "screen_changed=yes"
    return f"screen_changed=yes; {'; '.join(details)}"


def _linked_visual_change_summary(
    appeared: list[ObservedNodeChange],
    disappeared: list[ObservedNodeChange],
    updated: list[ObservedNodeChange],
) -> list[str]:
    return [
        f"{change.change_type} {change.label}"
        for change in [*appeared[:2], *disappeared[:2], *updated[:2]]
    ]


def _prioritize_business_changes(
    changes: list[ObservedNodeChange],
    package: str | None,
) -> list[ObservedNodeChange]:
    if not changes:
        return []
    if package:
        package_changes = [change for change in changes if change.stable_key.startswith(f"rid:{package}:")]
        if package_changes:
            return package_changes
    non_system_changes = [
        change for change in changes if not change.stable_key.startswith("rid:com.android.systemui:")
    ]
    return non_system_changes
