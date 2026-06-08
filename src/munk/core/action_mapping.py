from __future__ import annotations

from munk.agent_base.action import Action, ActionType


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

    if action.type == ActionType.CLICK and action.box:
        return Action.click(scale_box(action.box), summary=action.summary)
    if action.type == ActionType.CLICK and action.point:
        return Action.click_point(scale_point(action.point), summary=action.summary)
    if action.type == ActionType.LONG_PRESS and action.box:
        return Action.long_press(
            scale_box(action.box),
            duration=action.duration,
            summary=action.summary,
        )
    if action.type == ActionType.LONG_PRESS and action.point:
        return Action.long_press_point(
            scale_point(action.point),
            duration=action.duration,
            summary=action.summary,
        )
    if action.type == ActionType.CLEAR_AND_INPUT and action.box and action.text is not None:
        return Action.clear_and_input(
            scale_box(action.box),
            action.text,
            dismiss_keyboard=action.dismiss_keyboard is not False,
            summary=action.summary,
        )
    if action.type == ActionType.INPUT and action.text is not None:
        return Action.input_text(
            action.text,
            summary=action.summary,
            dismiss_keyboard=action.dismiss_keyboard,
        )
    if action.type in {ActionType.SCROLL, ActionType.SWIPE} and action.direction and action.distance_px is not None:
        scale = scale_y if action.direction in {"up", "down"} else scale_x
        scaled_distance = max(1, int(round(action.distance_px * scale)))
        if action.type == ActionType.SCROLL:
            return Action.scroll(
                direction=action.direction,
                distance_px=scaled_distance,
                summary=action.summary,
            )
        return Action.swipe(
            direction=action.direction,
            distance_px=scaled_distance,
            summary=action.summary,
        )
    return action
