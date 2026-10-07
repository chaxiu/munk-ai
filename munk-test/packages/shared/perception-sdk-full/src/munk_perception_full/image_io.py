from __future__ import annotations

from pathlib import Path
from typing import cast

import cv2
import numpy as np
from munk.perception.image import BgrImage


def load_image_bgr(path: Path, max_side: int) -> tuple[BgrImage, float]:
    data = np.fromfile(str(path), dtype=np.uint8)
    image = cast(BgrImage | None, cv2.imdecode(data, cv2.IMREAD_COLOR))
    if image is None:
        raise ValueError(f"failed to load image: {path}")
    scale = 1.0
    if max_side > 0:
        height = int(image.shape[0])
        width = int(image.shape[1])
        longest = max(height, width)
        if longest > max_side:
            scale = max_side / float(longest)
            new_size = (int(width * scale), int(height * scale))
            image = cast(BgrImage, cv2.resize(image, new_size, interpolation=cv2.INTER_AREA))
    return image, scale


def letterbox(
    image: BgrImage,
    new_size: int,
    color: tuple[int, int, int] = (114, 114, 114),
) -> tuple[BgrImage, float, tuple[int, int]]:
    height = int(image.shape[0])
    width = int(image.shape[1])
    scale = min(new_size / float(height), new_size / float(width))
    new_w = int(round(width * scale))
    new_h = int(round(height * scale))
    resized = cast(BgrImage, cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR))
    pad_w = new_size - new_w
    pad_h = new_size - new_h
    top = pad_h // 2
    bottom = pad_h - top
    left = pad_w // 2
    right = pad_w - left
    padded = cast(
        BgrImage,
        cv2.copyMakeBorder(resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color),
    )
    return padded, scale, (left, top)
