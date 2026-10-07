from __future__ import annotations

from pathlib import Path
from typing import cast

import cv2
from munk.agent_base.image_payload import encode_png_for_max_side
from munk.perception.image import BgrImage
from pydantic_ai.messages import BinaryImage


def load_screenshot_binary_image(
    path_value: str,
    *,
    identifier: str,
    vl_max_side: int,
) -> BinaryImage | None:
    path = Path(path_value)
    if not path.exists():
        return None
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        return BinaryImage(path.read_bytes(), media_type="image/png", identifier=identifier)
    png_bytes = encode_png_for_max_side(cast(BgrImage, image), vl_max_side)
    if not png_bytes:
        return None
    return BinaryImage(png_bytes, media_type="image/png", identifier=identifier)
