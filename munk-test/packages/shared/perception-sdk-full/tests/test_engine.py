from typing import cast

import numpy as np
from munk.perception.types import IconDetection, TextDetection
from munk_perception_full.engine import PerceptionEngine
from munk_perception_full.icon import IconDetector
from munk_perception_full.ocr import OcrEngine


class FakeIconDetector:
    def detect(self, image_bgr, conf_threshold=None):  # noqa: ANN001, ARG002
        return [
            IconDetection(box=(10, 10, 40, 40), score=0.9),
            IconDetection(box=(10, 170, 40, 195), score=0.8),
        ]


class FakeOcrEngine:
    def recognize(self, image_bgr):  # noqa: ANN001
        return [
            TextDetection(box=(60, 20, 140, 50), text="Title", score=0.95),
            TextDetection(box=(60, 170, 140, 195), text="Keyboard", score=0.92),
        ]


def build_engine() -> PerceptionEngine:
    engine = PerceptionEngine.__new__(PerceptionEngine)
    engine.icon_detector = cast(IconDetector, FakeIconDetector())
    engine.ocr_engine = cast(OcrEngine, FakeOcrEngine())
    engine.max_side = 400
    return engine


def test_analyze_filters_detections_inside_excluded_regions() -> None:
    engine = build_engine()
    image = np.zeros((200, 200, 3), dtype=np.uint8)

    elements = engine.analyze(image, excluded_regions=[(0, 150, 200, 200)])

    assert len(elements) == 2
    texts = {element.text for element in elements}
    assert "Title" in texts
    assert "Keyboard" not in texts


def test_analyze_masks_excluded_regions_before_detection() -> None:
    engine = build_engine()
    image = np.full((200, 200, 3), 255, dtype=np.uint8)

    elements = engine.analyze(image, excluded_regions=[(0, 150, 200, 200)])

    assert any(element.text == "Title" for element in elements)
