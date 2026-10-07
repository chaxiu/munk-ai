import numpy as np
from munk.perception.types import ClickableElement
from munk_perception_full.annotate import (
    _build_label_style,
    _choose_text_label_position,
    _measure_label,
    annotate_image,
)


def test_build_label_style_scales_with_canvas_size() -> None:
    web_style = _build_label_style((900, 1440), (100, 100, 220, 220))
    android_style = _build_label_style((2960, 1440), (100, 100, 220, 220))

    assert web_style.font_scale < android_style.font_scale
    assert web_style.thickness <= android_style.thickness
    assert web_style.border_thickness <= android_style.border_thickness


def test_build_label_style_caps_label_height_for_small_web_box() -> None:
    box = (1001, 15, 1053, 48)
    style = _build_label_style((900, 1440), box)

    _, label_h, _ = _measure_label("10", style)

    assert label_h <= 28


def test_build_label_style_grows_with_larger_box_on_same_canvas() -> None:
    small_style = _build_label_style((900, 1440), (10, 10, 62, 43))
    large_style = _build_label_style((900, 1440), (10, 10, 240, 150))

    assert small_style.font_scale <= large_style.font_scale
    assert small_style.pad <= large_style.pad


def test_annotate_image_draws_scaled_label_without_changing_shape() -> None:
    image = np.zeros((900, 1440, 3), dtype=np.uint8)
    element = ClickableElement(box=(1001, 15, 1053, 48), kind="icon", text="", score=0.9)

    annotated = annotate_image(image, [element])

    assert annotated.shape == image.shape
    assert np.count_nonzero(annotated) > 0


def test_choose_text_label_position_prefers_inside_top_left_for_large_box() -> None:
    image_shape = (900, 1440)
    box = (100, 120, 300, 280)
    style = _build_label_style(image_shape, box)
    label_w, label_h, _ = _measure_label("12", style)

    position = _choose_text_label_position(box, [box], label_w, label_h, image_shape, style)

    assert position == (box[0] + style.margin, box[1] + style.margin)


def test_choose_text_label_position_falls_back_outside_for_small_box() -> None:
    image_shape = (900, 1440)
    box = (100, 120, 130, 150)
    style = _build_label_style(image_shape, box)
    label_w, label_h, _ = _measure_label("12", style)

    position = _choose_text_label_position(box, [box], label_w, label_h, image_shape, style)

    assert position != (box[0] + style.margin, box[1] + style.margin)
