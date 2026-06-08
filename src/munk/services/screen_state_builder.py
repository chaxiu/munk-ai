from __future__ import annotations

from munk.agent_base.base import ObservationSnapshotSource, RuntimeObservationSnapshot, ScreenState
from munk.perception import ObservationTree, PerceptionAnalyzeRequest, PerceptionProvider
from munk.perception.image import BgrImage


def build_screen_state_from_observation_artifacts(
    *,
    perception: PerceptionProvider,
    screen_bgr: BgrImage,
    observation_tree: ObservationTree | None,
    entry_identity: str | None,
    surface_identity: str | None,
    platform: str | None,
    icon_conf: float,
    keyboard_visible: bool | None = None,
    keyboard_bounds: tuple[int, int, int, int] | None = None,
    keyboard_source: str | None = None,
    platform_context: dict[str, object] | None = None,
) -> ScreenState:
    image_h = int(screen_bgr.shape[0])
    image_w = int(screen_bgr.shape[1])
    analysis = perception.analyze_observation(
        PerceptionAnalyzeRequest(
            image_bgr=screen_bgr,
            screen_size=(image_w, image_h),
            current_app_identity=entry_identity,
            observation_tree=observation_tree,
            icon_conf=icon_conf,
            keyboard_visible=keyboard_visible,
            keyboard_bounds=keyboard_bounds,
            keyboard_source=keyboard_source,
        )
    )
    return ScreenState(
        elements=analysis.elements,
        screen_size=(image_w, image_h),
        entry_identity=entry_identity,
        surface_identity=surface_identity,
        image_bgr=screen_bgr,
        screen_frame=analysis.screen_frame,
        platform=platform,
        platform_context=platform_context,
    )


def build_runtime_observation_snapshot(
    *,
    perception: PerceptionProvider,
    screen_bgr: BgrImage,
    observation_tree: ObservationTree | None,
    entry_identity: str | None,
    surface_identity: str | None,
    platform: str | None,
    icon_conf: float,
    source: ObservationSnapshotSource,
    keyboard_visible: bool | None = None,
    keyboard_bounds: tuple[int, int, int, int] | None = None,
    keyboard_source: str | None = None,
    platform_context: dict[str, object] | None = None,
) -> RuntimeObservationSnapshot:
    screen = build_screen_state_from_observation_artifacts(
        perception=perception,
        screen_bgr=screen_bgr,
        observation_tree=observation_tree,
        entry_identity=entry_identity,
        surface_identity=surface_identity,
        platform=platform,
        icon_conf=icon_conf,
        keyboard_visible=keyboard_visible,
        keyboard_bounds=keyboard_bounds,
        keyboard_source=keyboard_source,
        platform_context=platform_context,
    )
    return RuntimeObservationSnapshot(
        screen=screen,
        observation_tree=observation_tree,
        icon_conf=icon_conf,
        source=source,
    )
