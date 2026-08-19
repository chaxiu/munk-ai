from __future__ import annotations

from munk.core.action_target_models import TargetHandle

STRUCTURE_ELEMENT_HANDLE_KINDS = frozenset({"dom", "a11y"})


def is_structure_element_handle(handle: TargetHandle | None) -> bool:
    """True when handle can drive SupportsElementTargetAction (DOM or a11y)."""
    return handle is not None and handle.kind in STRUCTURE_ELEMENT_HANDLE_KINDS
