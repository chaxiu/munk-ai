from __future__ import annotations

from dataclasses import replace

from munk.agent_base.action import Action, ActionType
from munk.core.action_target_models import TargetHandle


def map_action_to_device(
    action: Action,
    image_size: tuple[int, int],
    device_size: tuple[int, int],
) -> Action:
    image_w, image_h = image_size
    device_w, device_h = device_size
    if image_w <= 0 or image_h <= 0 or device_w <= 0 or device_h <= 0:
        return action
    if image_w == device_w and image_h == device_h:
        return action
    scale_x = device_w / float(image_w)
    scale_y = device_h / float(image_h)

    def scale_point(point: tuple[int, int]) -> tuple[int, int]:
        x = int(round(point[0] * scale_x))
        y = int(round(point[1] * scale_y))
        x = max(0, min(device_w - 1, x))
        y = max(0, min(device_h - 1, y))
        return x, y

    def scale_box(box: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        x1, y1, x2, y2 = box
        x1 = int(round(x1 * scale_x))
        y1 = int(round(y1 * scale_y))
        x2 = int(round(x2 * scale_x))
        y2 = int(round(y2 * scale_y))
        x1 = max(0, min(device_w - 1, x1))
        y1 = max(0, min(device_h - 1, y1))
        x2 = max(0, min(device_w - 1, x2))
        y2 = max(0, min(device_h - 1, y2))
        return x1, y1, x2, y2

    def scale_handle(handle: TargetHandle | None) -> TargetHandle | None:
        if handle is None or handle.box is None:
            return handle
        return replace(handle, box=scale_box(handle.box))

    if action.type == ActionType.CLICK and action.box:
        return Action.click(
            scale_box(action.box),
            summary=action.summary,
            handle=scale_handle(action.handle),
            target_ref=action.target_ref,
        )
    if action.type == ActionType.CLICK and action.point:
        return Action.click_point(scale_point(action.point), summary=action.summary)
    if action.type == ActionType.LONG_PRESS and action.box:
        return Action.long_press(
            scale_box(action.box),
            duration=action.duration,
            summary=action.summary,
            handle=scale_handle(action.handle),
            target_ref=action.target_ref,
        )
    if action.type == ActionType.LONG_PRESS and action.point:
        return Action.long_press_point(
            scale_point(action.point),
            duration=action.duration,
            summary=action.summary,
        )
    if action.type == ActionType.EDIT_TEXT and action.text is not None:
        return Action.edit_text(
            text=action.text,
            mode=action.text_mode or "append",
            target_box=scale_box(action.box) if action.box is not None else None,
            dismiss_keyboard=action.dismiss_keyboard,
            summary=action.summary,
            handle=scale_handle(action.handle),
            target_ref=action.target_ref,
        )
    if action.type == ActionType.SET_VALUE and action.text is not None and action.handle is not None:
        scaled_handle = scale_handle(action.handle)
        assert scaled_handle is not None
        return Action.set_value(
            value=action.text,
            handle=scaled_handle,
            target_ref=action.target_ref or "",
            summary=action.summary,
        )
    if action.type == ActionType.INPUT and action.text is not None:
        return Action.input_text(
            action.text,
            summary=action.summary,
            dismiss_keyboard=action.dismiss_keyboard,
        )
    if action.type == ActionType.PULL_TO_REFRESH:
        return Action.pull_to_refresh(
            start_x_ratio=action.start_x_ratio,
            start_y_ratio=action.start_y_ratio,
            distance_ratio=action.distance_ratio,
            summary=action.summary,
        )
    if action.type == ActionType.DRAG and action.start is not None and action.end is not None:
        return Action.drag(
            start=scale_point(action.start),
            end=scale_point(action.end),
            duration=action.duration,
            summary=action.summary,
        )
    if (
        action.type in {ActionType.SCROLL, ActionType.SWIPE}
        and action.direction
        and action.start_x_ratio is not None
        and action.start_y_ratio is not None
        and action.distance_ratio is not None
    ):
        if action.type == ActionType.SCROLL:
            return Action.scroll(
                direction=action.direction,
                start_x_ratio=action.start_x_ratio,
                start_y_ratio=action.start_y_ratio,
                distance_ratio=action.distance_ratio,
                summary=action.summary,
            )
        return Action.swipe(
            direction=action.direction,
            start_x_ratio=action.start_x_ratio,
            start_y_ratio=action.start_y_ratio,
            distance_ratio=action.distance_ratio,
            summary=action.summary,
        )
    return action
