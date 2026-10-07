from __future__ import annotations

from pathlib import Path
from typing import cast

import cv2
from munk.agent_base.image_payload import encode_image_for_max_side
from munk.perception.image import BgrImage
from pydantic_ai.messages import BinaryImage


def load_screenshot_binary_image(
    path_value: str | Path,
    *,
    identifier: str,
    vl_max_side: int,
    vl_image_format: str,
    vl_fallback_image_format: str,
    vl_webp_quality: int,
    vl_jpeg_quality: int,
) -> BinaryImage | None:
    path = Path(path_value)
    if not path.exists():
        return None
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        return BinaryImage(path.read_bytes(), media_type="image/png", identifier=identifier)
    payload = encode_image_for_max_side(
        cast(BgrImage, image),
        vl_max_side,
        preferred_format=vl_image_format,
        fallback_format=vl_fallback_image_format,
        webp_quality=vl_webp_quality,
        jpeg_quality=vl_jpeg_quality,
    )
    if payload is None:
        return None
    return BinaryImage(payload.data, media_type=payload.media_type, identifier=identifier)
