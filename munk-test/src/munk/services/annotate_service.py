from __future__ import annotations

from pathlib import Path
from typing import cast

import cv2
import numpy as np

from munk.config.schema import MunkConfig
from munk.perception.image import BgrImage
from munk.services.models import AnnotateRequest, AnnotateResult
from munk.services.perception_runtime import build_perception_provider_for_runtime


class AnnotateService:
    def run(self, request: AnnotateRequest) -> AnnotateResult:
        if not request.image_path.exists():
            raise FileNotFoundError(request.image_path)

        output_path = request.output_path
        if output_path is None:
            output_path = request.image_path.with_name(f"{request.image_path.stem}_annotated.png")

        image_bgr, _ = load_image_bgr(request.image_path, max_side=request.max_side)
        config = request.resolved_config.config if request.resolved_config is not None else MunkConfig()
        provider = build_perception_provider_for_runtime(
            config,
            max_side=request.max_side,
            icon_conf=request.icon_conf,
        )
        elements = provider.analyze_image(image_bgr, icon_conf=request.icon_conf)
        annotated = provider.annotate_image(image_bgr, elements)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output_path), annotated)
        return AnnotateResult(output_path=output_path, element_count=len(elements))


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
