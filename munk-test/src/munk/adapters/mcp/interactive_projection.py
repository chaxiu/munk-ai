from __future__ import annotations

from typing import Literal, TypeAlias

from munk.agent_base.image_payload import encode_image_for_max_side
from munk.core.action_target_models import VISION_PART_MAX
from munk.core.action_target_text import (
    DEFAULT_TARGET_PART_LIMIT,
    TargetListSource,
    build_targets_list_text,
    build_targets_match_text,
    build_targets_text,
    clamp_target_part_limit,
    measure_targets_list_window,
    measure_targets_seed_window,
)
from munk.services.interactive import InteractiveObservation, InteractiveTargetSummary
from munk.services.interactive.screenshot_storage import write_interactive_screenshot

from .device_tool_outputs import (
    InteractiveObservationData,
    InteractiveScreenData,
    InteractiveTargetCompactData,
    InteractiveTargetData,
    SessionListTargetsData,
    SessionObserveMatchData,
    SessionObserveObservationData,
)

ObservationDetail: TypeAlias = Literal["compact", "full"]
COMPACT_TARGET_LIMIT = 20

OBSERVE_TRUNCATION_GUIDANCE = (
    "Observation window is truncated. Call session_list_targets "
    "with source/offset/limit on this session to page the same "
    "snapshot without re-observing. Re-observe only if the UI changed."
)


def build_observe_payload(
    observation: InteractiveObservation,
    *,
    include_screenshot: bool = False,
    match: str | None = None,
) -> SessionObserveObservationData:
    window = measure_targets_seed_window(
        observation.screen,
        prompt_max_elements=VISION_PART_MAX,
    )
    targets_text = build_targets_text(
        observation.screen,
        max_elements=VISION_PART_MAX * 2,
        prompt_max_elements=VISION_PART_MAX,
    )
    screenshot_mime_type, screenshot_path = _build_screenshot_payload(
        observation,
        include_screenshot=include_screenshot,
    )
    match_payload = _build_match_payload(observation, match=match)
    return SessionObserveObservationData(
        captured_at=observation.captured_at,
        summary=observation.summary,
        screen=_build_screen_data(observation),
        targets_text=targets_text,
        total_vision=window.total_vision,
        total_tree=window.total_tree,
        returned_vision=window.returned_vision,
        returned_tree=window.returned_tree,
        truncated=window.truncated,
        guidance=OBSERVE_TRUNCATION_GUIDANCE if window.truncated else None,
        tree_status=observation.tree_status,
        tree_error=observation.tree_error,
        match=match_payload,
        screenshot_mime_type=screenshot_mime_type,
        screenshot_path=screenshot_path,
    )


def build_list_targets_payload(
    observation: InteractiveObservation,
    *,
    source: TargetListSource = "all",
    offset: int = 0,
    limit: int | None = None,
) -> SessionListTargetsData:
    resolved_limit = clamp_target_part_limit(limit if limit is not None else DEFAULT_TARGET_PART_LIMIT)
    window = measure_targets_list_window(
        observation.screen,
        offset=offset,
        limit=resolved_limit,
        source=source,
    )
    targets_text = build_targets_list_text(
        observation.screen,
        offset=offset,
        limit=resolved_limit,
        source=source,
    )
    return SessionListTargetsData(
        source=source,
        offset=max(offset, 0),
        limit=resolved_limit,
        targets_text=targets_text,
        total_vision=window.total_vision,
        total_tree=window.total_tree,
        returned_vision=window.returned_vision,
        returned_tree=window.returned_tree,
        truncated=window.truncated,
        next_offset=window.next_offset,
        tree_status=observation.tree_status,
        tree_error=observation.tree_error,
    )


def build_observation_payload(
    observation: InteractiveObservation,
    *,
    detail: ObservationDetail,
    include_screenshot: bool = False,
    target_limit: int = COMPACT_TARGET_LIMIT,
) -> InteractiveObservationData:
    """Legacy projection retained for session_act before/after payloads."""
    screen = observation.screen
    total_target_count = len(observation.targets)
    compact = detail == "compact"
    projected_targets = observation.targets[:target_limit] if compact else observation.targets
    screenshot_mime_type, screenshot_path = _build_screenshot_payload(
        observation,
        include_screenshot=include_screenshot,
    )
    return InteractiveObservationData(
        detail="compact" if compact else "full",
        captured_at=observation.captured_at,
        summary=observation.summary,
        screen=InteractiveScreenData(
            screen_size=screen.screen_size,
            entry_identity=screen.entry_identity,
            surface_identity=screen.surface_identity,
            platform=screen.platform,
            element_count=len(screen.elements),
            platform_context=screen.platform_context,
        ),
        total_target_count=total_target_count,
        returned_target_count=len(projected_targets),
        truncated=compact and len(projected_targets) < total_target_count,
        targets=[
            _build_compact_target_data(target) if compact else _build_target_data(target)
            for target in projected_targets
        ],
        screenshot_mime_type=screenshot_mime_type,
        screenshot_path=screenshot_path,
    )


def _build_screen_data(observation: InteractiveObservation) -> InteractiveScreenData:
    screen = observation.screen
    return InteractiveScreenData(
        screen_size=screen.screen_size,
        entry_identity=screen.entry_identity,
        surface_identity=screen.surface_identity,
        platform=screen.platform,
        element_count=len(screen.elements),
        platform_context=screen.platform_context,
    )


def _build_match_payload(
    observation: InteractiveObservation,
    *,
    match: str | None,
) -> SessionObserveMatchData | None:
    if match is None or not str(match).strip():
        return None
    result = build_targets_match_text(observation.screen, match)
    return SessionObserveMatchData(
        query=result.query,
        matched_count=result.matched_count,
        match_text=result.match_text,
    )


def _build_compact_target_data(target: InteractiveTargetSummary) -> InteractiveTargetCompactData:
    return InteractiveTargetCompactData(
        target_ref=target.target_ref,
        source=target.source,
        box=target.box,
        label=target.label,
        text=target.text,
    )


def _build_target_data(target: InteractiveTargetSummary) -> InteractiveTargetData:
    return InteractiveTargetData(
        target_ref=target.target_ref,
        label=target.label,
        kind=target.kind,
        source=target.source,
        box=target.box,
        resource_id=target.resource_id,
        text=target.text,
    )


def _build_screenshot_payload(
    observation: InteractiveObservation,
    *,
    include_screenshot: bool,
) -> tuple[str | None, str | None]:
    if not include_screenshot:
        return None, None
    image_bgr = observation.annotated_image_bgr
    if image_bgr is None:
        image_bgr = observation.screen.image_bgr
    if image_bgr is None:
        return None, None
    payload = encode_image_for_max_side(
        image_bgr,
        observation.vl_max_side,
        preferred_format=observation.vl_image_format,
        fallback_format=observation.vl_fallback_image_format,
        webp_quality=observation.vl_webp_quality,
        jpeg_quality=observation.vl_jpeg_quality,
    )
    if payload is None:
        return None, None
    screenshot_path = write_interactive_screenshot(
        session_id=observation.session_id,
        captured_at=observation.captured_at,
        image_bytes=payload.data,
        image_format=payload.image_format,
    )
    return payload.media_type, str(screenshot_path)
