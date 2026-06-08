from __future__ import annotations

from typing import Any, cast

import cv2

from munk.agent_base.base import ScreenState
from munk.core import observe_action_result, to_json_dict
from munk.core.action_targets import (
    ActionTarget,
    build_action_targets,
    build_recording_action_summary,
    degrade_target_confidence,
    resolve_recording_action_targets,
    summarize_action_target,
)
from munk.perception import ObservationTree, PerceptionProvider
from munk.perception.image import BgrImage
from munk.services.screen_state_builder import build_screen_state_from_observation_artifacts

MAX_TARGET_CANDIDATES = 3
DEFAULT_MAX_TARGETS = 80


def enrich_recording_bundle_for_analysis(
    bundle: dict[str, Any],
    *,
    perception: PerceptionProvider,
    icon_conf: float,
    max_targets: int = DEFAULT_MAX_TARGETS,
) -> dict[str, Any]:
    session = cast(dict[str, Any], bundle.get("session") or {})
    session_app_target = cast(dict[str, Any], session.get("app_target") or {})
    platform = cast(str | None, session_app_target.get("platform"))
    step_payloads = cast(list[dict[str, Any]], bundle.get("steps") or [])
    observation_cache: dict[str, ScreenState] = {}
    for step in step_payloads:
        before_screen = _load_screen_state(
            step=step,
            role="before",
            platform=platform,
            perception=perception,
            icon_conf=icon_conf,
            observation_cache=observation_cache,
        )
        after_screen = _load_screen_state(
            step=step,
            role="after",
            platform=platform,
            perception=perception,
            icon_conf=icon_conf,
            observation_cache=observation_cache,
        )
        before_targets = build_action_targets(before_screen, max_elements=max_targets)
        action_evidence = _build_action_evidence(
            step=step,
            before_screen=before_screen,
            after_screen=after_screen,
            before_targets=before_targets,
        )
        outcome_evidence = _build_outcome_evidence(
            step=step,
            before_screen=before_screen,
            after_screen=after_screen,
        )
        page_identity = {
            "before_entry_identity": before_screen.entry_identity,
            "after_entry_identity": after_screen.entry_identity,
            "before_surface_identity": before_screen.surface_identity,
            "after_surface_identity": after_screen.surface_identity,
        }
        step["page_identity"] = page_identity
        step["action_evidence"] = action_evidence
        step["outcome_evidence"] = outcome_evidence
    return bundle


def _load_screen_state(
    *,
    step: dict[str, Any],
    role: str,
    platform: str | None,
    perception: PerceptionProvider,
    icon_conf: float,
    observation_cache: dict[str, ScreenState],
) -> ScreenState:
    observation_payload = cast(dict[str, Any], step[f"{role}_observation"])
    observation = cast(dict[str, Any], observation_payload["observation"])
    observation_id = cast(str, observation["observation_id"])
    cached = observation_cache.get(observation_id)
    if cached is not None:
        return cached
    screenshot = cast(dict[str, Any], step[f"{role}_screenshot"])
    image = cv2.imread(cast(str, screenshot["path"]), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"unable to load recording screenshot: {screenshot['path']}")
    image_bgr = cast(BgrImage, image)
    tree_text = cast(str | None, observation_payload.get("tree_text"))
    observation_tree = _build_observation_tree(platform=platform, tree_text=tree_text)
    screen = build_screen_state_from_observation_artifacts(
        perception=perception,
        screen_bgr=image_bgr,
        observation_tree=observation_tree,
        entry_identity=cast(str | None, observation.get("entry_identity")),
        surface_identity=_observation_surface_identity(observation),
        platform=platform,
        icon_conf=icon_conf,
        keyboard_visible=None,
        keyboard_bounds=None,
        keyboard_source=None,
        platform_context=None,
    )
    observation_cache[observation_id] = screen
    return screen


def _build_observation_tree(*, platform: str | None, tree_text: str | None) -> ObservationTree | None:
    if not tree_text:
        return None
    if platform == "ios":
        return ObservationTree(source_type="ios_ax_tree", content_type="json", payload=tree_text)
    if platform == "web":
        return ObservationTree(source_type="web_dom", content_type="html", payload=tree_text)
    return ObservationTree(source_type="android_uixml", content_type="xml", payload=tree_text)


def _build_action_evidence(
    *,
    step: dict[str, Any],
    before_screen,
    after_screen,
    before_targets: list[ActionTarget],
) -> dict[str, Any]:
    entry = cast(dict[str, Any], step["entry"])
    kind = cast(str, entry.get("kind") or "click")
    recording_event = cast(dict[str, Any] | None, step.get("recording_event"))
    forwarding_event = cast(dict[str, Any] | None, step.get("forwarding_event"))
    resolution = resolve_recording_action_targets(
        action_kind=kind,
        targets=before_targets,
        recording_event=recording_event,
        forwarding_event=forwarding_event,
        max_candidates=MAX_TARGET_CANDIDATES,
    )
    resolved_payload = _target_payload(resolution.resolved_target, confidence=resolution.confidence)
    candidate_payloads: list[dict[str, Any]] = [
        {
            **cast(dict[str, Any], summarize_action_target(candidate) or {}),
            "rank": index,
            "confidence": (
                resolution.confidence
                if index == 1
                else degrade_target_confidence(resolution.confidence, index=index)
            ),
        }
        for index, candidate in enumerate(resolution.candidates, start=1)
    ]
    return {
        "action_kind": kind,
        "raw_action_summary": build_recording_action_summary(
            action_kind=kind,
            recording_event=recording_event,
            forwarding_event=forwarding_event,
        ),
        "before_entry_identity": before_screen.entry_identity,
        "after_entry_identity": after_screen.entry_identity,
        "before_surface_identity": before_screen.surface_identity,
        "after_surface_identity": after_screen.surface_identity,
        "resolved_target": resolved_payload,
        "target_candidates": candidate_payloads,
        "warnings": resolution.warnings,
    }


def _build_outcome_evidence(
    *,
    step: dict[str, Any],
    before_screen,
    after_screen,
) -> dict[str, Any]:
    del step
    observation = observe_action_result(before_screen, after_screen)
    screen_diff = observation.screen_diff
    warnings: list[str] = []
    if screen_diff is None:
        warnings.append("screen diff is unavailable")
    return {
        "screen_diff_summary": observation.summary,
        "screen_diff": to_json_dict(screen_diff) if screen_diff is not None else {},
        "before_entry_identity": before_screen.entry_identity,
        "after_entry_identity": after_screen.entry_identity,
        "before_surface_identity": before_screen.surface_identity,
        "after_surface_identity": after_screen.surface_identity,
        "warnings": warnings,
    }


def _target_payload(target: ActionTarget | None, *, confidence: float | None) -> dict[str, Any] | None:
    payload = cast(dict[str, Any] | None, summarize_action_target(target))
    if payload is None:
        return None
    payload["confidence"] = confidence
    return payload


def _observation_surface_identity(observation: dict[str, Any]) -> str | None:
    surface_identity = observation.get("surface_identity")
    if isinstance(surface_identity, str) and surface_identity.strip():
        return surface_identity
    current_app_state = observation.get("current_app_state")
    if isinstance(current_app_state, dict):
        candidate = cast(object | None, current_app_state.get("surface_identity"))
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    return None
