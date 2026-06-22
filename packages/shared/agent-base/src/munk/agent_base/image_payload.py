from __future__ import annotations
from dataclasses import dataclass

from collections.abc import Callable
from typing import cast

import cv2

from munk.perception.image import BgrImage

ImageFormat = str


@dataclass(frozen=True)
class EncodedImagePayload:
    data: bytes
    media_type: str
    image_format: ImageFormat


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


def _encode_image(image_bgr: BgrImage, *, extension: str, params: list[int] | None = None) -> bytes:
    ok, buf = cv2.imencode(extension, image_bgr, params or [])
    if not ok:
        return b""
    return buf.tobytes()


def encode_png_for_max_side(image_bgr: BgrImage, max_side: int) -> bytes:
    resized, _ = resize_for_max_side(image_bgr, max_side)
    return _encode_image(resized, extension=".png")


def encode_webp_for_max_side(image_bgr: BgrImage, max_side: int, *, quality: int = 80) -> bytes:
    resized, _ = resize_for_max_side(image_bgr, max_side)
    return _encode_image(resized, extension=".webp", params=[cv2.IMWRITE_WEBP_QUALITY, quality])


def encode_jpeg_for_max_side(image_bgr: BgrImage, max_side: int, *, quality: int = 82) -> bytes:
    resized, _ = resize_for_max_side(image_bgr, max_side)
    return _encode_image(resized, extension=".jpg", params=[cv2.IMWRITE_JPEG_QUALITY, quality])


def encode_image_for_max_side(
    image_bgr: BgrImage,
    max_side: int,
    *,
    preferred_format: ImageFormat = "webp",
    fallback_format: ImageFormat = "jpeg",
    webp_quality: int = 80,
    jpeg_quality: int = 82,
) -> EncodedImagePayload | None:
    encoders: dict[ImageFormat, tuple[str, Callable[[BgrImage, int], bytes]]] = {
        "png": ("image/png", lambda img, side: encode_png_for_max_side(img, side)),
        "webp": (
            "image/webp",
            lambda img, side: encode_webp_for_max_side(img, side, quality=webp_quality),
        ),
        "jpeg": (
            "image/jpeg",
            lambda img, side: encode_jpeg_for_max_side(img, side, quality=jpeg_quality),
        ),
    }
    for image_format in (preferred_format, fallback_format):
        encoder = encoders.get(image_format)
        if encoder is None:
            continue
        media_type, encode = encoder
        encoded = encode(image_bgr, max_side)
        if encoded:
            return EncodedImagePayload(
                data=encoded,
                media_type=media_type,
                image_format=image_format,
            )
    return None
