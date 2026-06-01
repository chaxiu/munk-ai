from __future__ import annotations

from typing import cast

import cv2

from munk.perception.image import BgrImage


def resize_for_max_side(image_bgr: BgrImage, max_side: int) -> tuple[BgrImage, float]:
    if max_side <= 0:
        return image_bgr, 1.0
    height = int(image_bgr.shape[0])
    width = int(image_bgr.shape[1])
    longest = max(height, width)
    if longest <= max_side or longest == 0:
        return image_bgr, 1.0
    scale = max_side / float(longest)
    new_size = (int(round(width * scale)), int(round(height * scale)))
    resized = cast(BgrImage, cv2.resize(image_bgr, new_size, interpolation=cv2.INTER_AREA))
    return resized, scale


def encode_png_for_max_side(image_bgr: BgrImage, max_side: int) -> bytes:
    resized, _ = resize_for_max_side(image_bgr, max_side)
    ok, buf = cv2.imencode(".png", resized)
    if not ok:
        return b""
    return buf.tobytes()
