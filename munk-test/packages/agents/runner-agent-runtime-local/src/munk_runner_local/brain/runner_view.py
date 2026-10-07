from __future__ import annotations

from typing import Literal

from munk.agent_base.base import ScreenState

from munk.core.action_target_text import (
    build_target_detail_text as _build_target_detail_text,
)
from munk.core.action_target_text import (
    build_targets_list_text as _build_targets_list_text,
)
from munk.core.action_target_text import (
    build_targets_text as _build_targets_text,
)
from munk.core.action_target_text import (
    count_targets_in_text as _count_targets_in_text,
)
from munk.core.action_targets import (
    build_action_targets,
    resolve_action_target,
)

__all__ = [
    "build_action_targets",
    "build_target_detail_text",
    "build_targets_list_text",
    "build_targets_text",
    "count_targets_in_text",
    "resolve_action_target",
]


def build_targets_text(
    screen: ScreenState,
    max_elements: int,
    prompt_max_elements: int,
) -> str:
    return _build_targets_text(screen, max_elements, prompt_max_elements)


def build_targets_list_text(
    screen: ScreenState,
    *,
    offset: int,
    limit: int,
    source: Literal["all", "vision", "tree"] = "all",
) -> str:
    return _build_targets_list_text(screen, offset=offset, limit=limit, source=source)


def build_target_detail_text(screen: ScreenState, *, target_ref: str, max_elements: int) -> str:
    return _build_target_detail_text(screen, target_ref=target_ref, max_elements=max_elements)


def count_targets_in_text(text: str) -> int:
    return _count_targets_in_text(text)
