from __future__ import annotations

from munk.agent_base.base import ScreenState
from munk.core.action_target_building import build_canonical_target_parts
from munk.core.action_target_models import ActionTarget

from .models import InteractiveObservation, InteractiveTargetSummary

__all__ = [
    "build_interactive_target_catalog",
    "interactive_targets_for_resolution",
]


def build_interactive_target_catalog(screen: ScreenState) -> list[InteractiveTargetSummary]:
    """Build the full canonical vN/tN catalog from screen (same identity space as list/match)."""
    parts = build_canonical_target_parts(screen)
    return [
        _summary_from_action_target(target)
        for target in [*parts.vision_targets, *parts.tree_targets]
    ]


def interactive_targets_for_resolution(
    observation: InteractiveObservation,
) -> list[InteractiveTargetSummary]:
    """Prefer screen canonical catalog so act resolve/rebind matches list/match refs.

    Empty-screen fixtures (unit tests) fall back to observation.targets.
    """
    catalog = build_interactive_target_catalog(observation.screen)
    if catalog:
        return catalog
    return list(observation.targets)


def _summary_from_action_target(target: ActionTarget) -> InteractiveTargetSummary:
    return InteractiveTargetSummary(
        target_ref=target.ref or f"{target.channel}{target.index}",
        channel=target.channel,
        index=target.index,
        label=target.label,
        kind=target.kind,
        source=target.source,
        box=target.box,
        resource_id=target.resource_id,
        text=target.text,
        handle=target.handle,
    )
