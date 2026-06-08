from __future__ import annotations

from typing import Literal, TypeAlias

from munk.agent_base.image_payload import encode_png_for_max_side
from munk.services.interactive import InteractiveObservation, InteractiveTargetSummary
from munk.services.interactive.screenshot_storage import write_interactive_screenshot

from .device_tool_outputs import (
    InteractiveObservationData,
    InteractiveScreenData,
    InteractiveTargetCompactData,
    InteractiveTargetData,
)

ObservationDetail: TypeAlias = Literal["compact", "full"]
COMPACT_TARGET_LIMIT = 20


def build_observation_payload(
    observation: InteractiveObservation,
    *,
    detail: ObservationDetail,
    include_screenshot: bool = False,
    target_limit: int = COMPACT_TARGET_LIMIT,
) -> InteractiveObservationData:
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


def _build_compact_target_data(target: InteractiveTargetSummary) -> InteractiveTargetCompactData:
    return InteractiveTargetCompactData(
        target_id=target.target_id,
        source=target.source,
        box=target.box,
        label=target.label,
        text=target.text,
    )


def _build_target_data(target: InteractiveTargetSummary) -> InteractiveTargetData:
    return InteractiveTargetData(
        target_id=target.target_id,
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
    image_bytes = encode_png_for_max_side(image_bgr, observation.vl_max_side)
    if not image_bytes:
        return None, None
    screenshot_path = write_interactive_screenshot(
        session_id=observation.session_id,
        captured_at=observation.captured_at,
        image_bytes=image_bytes,
    )
    return "image/png", str(screenshot_path)
