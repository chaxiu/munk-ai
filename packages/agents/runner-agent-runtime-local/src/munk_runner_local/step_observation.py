from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

import cv2
from munk.agent_base.base import RuntimeObservationSnapshot, ScreenState
from munk.core.action_targets import build_target_parts
from munk.perception import ObservationTree, to_json_dict
from munk.perception.image import BgrImage
from munk.services.settle import SettleComparableSnapshot

from .context import RunContext


@dataclass(frozen=True)
class StepObservationState:
    screen_bgr: BgrImage
    screen: ScreenState
    settle_before: SettleComparableSnapshot
    device_size: tuple[int, int]


def refresh_step_observation_state(
    *,
    context: RunContext,
    step_index: int,
    icon_conf: float,
    raw_path: Path,
    capture_screen_state: Callable[..., RuntimeObservationSnapshot],
    capture_settle_snapshot: Callable[..., SettleComparableSnapshot],
    preserve_feedback_from: ScreenState | None = None,
) -> StepObservationState:
    device_size = context.device.window_size()
    screen_bgr = context.device.screenshot_bgr()
    cv2.imwrite(str(raw_path), screen_bgr)
    snapshot = capture_screen_state(
        context=context,
        screen_bgr=screen_bgr,
        icon_conf=icon_conf,
        source="step_pre_action",
        device_size=device_size,
    )
    screen = snapshot.screen
    if preserve_feedback_from is not None:
        screen = replace(
            screen,
            last_action_observation=preserve_feedback_from.last_action_observation,
            last_action_feedback=preserve_feedback_from.last_action_feedback,
        )
    screen = replace(
        screen,
        action_target_parts=build_target_parts(
            screen,
            vision_limit=context.params.runner_max_elements,
            tree_limit=context.params.runner_max_elements,
        ),
    )
    write_observation_artifacts(context, step_index, screen, snapshot.observation_tree)
    settle_before = capture_settle_snapshot(
        context=context,
        screen_bgr=screen_bgr,
        observation_tree=snapshot.observation_tree,
        device_size=device_size,
    )
    return StepObservationState(
        screen_bgr=screen_bgr,
        screen=screen,
        settle_before=settle_before,
        device_size=device_size,
    )


def write_observation_artifacts(
    context: RunContext,
    step_index: int,
    screen: ScreenState,
    observation_tree: ObservationTree | None,
) -> None:
    frame_dir = context.paths.observation_frames_dir
    diff_dir = context.paths.observation_diffs_dir
    tree_dir = context.paths.observation_tree_dir
    if frame_dir is not None and screen.screen_frame is not None:
        frame_path = frame_dir / f"step_{step_index:04d}.json"
        frame_path.write_text(
            json.dumps(to_json_dict(screen.screen_frame), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if diff_dir is not None and screen.last_action_observation is not None and screen.last_action_observation.screen_diff is not None:
        diff_path = diff_dir / f"step_{step_index:04d}.json"
        diff_path.write_text(
            json.dumps(to_json_dict(screen.last_action_observation.screen_diff), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if tree_dir is not None and observation_tree is not None:
        suffix = {
            "xml": ".xml",
            "json": ".json",
            "html": ".html",
        }[observation_tree.content_type]
        tree_path = tree_dir / f"step_{step_index:04d}{suffix}"
        tree_path.write_text(observation_tree.payload, encoding="utf-8")
