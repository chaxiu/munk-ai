from __future__ import annotations

import logging
import time
from dataclasses import replace
from pathlib import Path
from typing import TypeVar, cast

import cv2
from munk.perception.image import BgrImage
from munk.perception.types import ClickableElement, IconDetection, TextDetection

from .fusion import fuse_elements
from .icon import IconDetector
from .ocr import OcrEngine

DetectionT = TypeVar("DetectionT", IconDetection, TextDetection)


class PerceptionEngine:
    def __init__(
        self,
        icon_model_path: Path,
        det_model_path: Path,
        det_config_path: Path | None,
        rec_model_path: Path,
        rec_yaml_path: Path,
        rec_keys_path: Path,
        cls_model_path: Path,
        max_side: int = 1600,
        icon_conf: float = 0.12,
        ocr_det_target_long_side: int | None = None,
        ocr_det_db_thresh: float | None = None,
        ocr_det_box_thresh: float | None = None,
        ocr_det_unclip_ratio: float | None = None,
        ocr_rec_score_thresh: float = 0.72,
    ) -> None:
        self.icon_detector = IconDetector(
            icon_model_path,
            input_size=1280,
            conf_threshold=icon_conf,
        )
        self.ocr_engine = OcrEngine(
            det_model_path,
            det_config_path,
            rec_model_path,
            rec_yaml_path,
            rec_keys_path,
            cls_model_path,
            det_target_long_side=ocr_det_target_long_side,
            det_db_thresh=ocr_det_db_thresh,
            det_box_thresh=ocr_det_box_thresh,
            det_unclip_ratio=ocr_det_unclip_ratio,
            rec_score_thresh=ocr_rec_score_thresh,
        )
        self.max_side = max_side

    def analyze(
        self,
        image_bgr: BgrImage,
        icon_conf: float | None = None,
        excluded_regions: list[tuple[int, int, int, int]] | None = None,
    ) -> list[ClickableElement]:
        started = time.perf_counter()
        resized, scale = self._resize_for_max_side(image_bgr, self.max_side)
        scaled_regions = self._scale_regions(excluded_regions or [], scale)
        masked = self._mask_regions(resized, scaled_regions)
        icon_started = time.perf_counter()
        icons = self._filter_detections_by_excluded_regions(
            self.icon_detector.detect(masked, conf_threshold=icon_conf),
            scaled_regions,
        )
        icon_ms = (time.perf_counter() - icon_started) * 1000.0
        ocr_started = time.perf_counter()
        texts = self._filter_detections_by_excluded_regions(
            self.ocr_engine.recognize(masked),
            scaled_regions,
        )
        ocr_ms = (time.perf_counter() - ocr_started) * 1000.0
        fuse_started = time.perf_counter()
        elements = fuse_elements(icons, texts)
        fuse_ms = (time.perf_counter() - fuse_started) * 1000.0
        total_ms = (time.perf_counter() - started) * 1000.0
        logging.info(
            "perception_timing total_ms=%.1f icon_ms=%.1f ocr_ms=%.1f fuse_ms=%.1f "
            "icons=%s texts=%s elements=%s scale=%.3f excluded_regions=%s",
            total_ms,
            icon_ms,
            ocr_ms,
            fuse_ms,
            len(icons),
            len(texts),
            len(elements),
            scale,
            len(scaled_regions),
        )
        if scale == 1.0:
            return elements
        scaled: list[ClickableElement] = []
        for element in elements:
            scaled_box = self._scale_box(element.box, 1.0 / scale)
            scaled.append(replace(element, box=scaled_box))
        return scaled

    def analyze_text(
        self,
        image_bgr: BgrImage,
        *,
        excluded_regions: list[tuple[int, int, int, int]] | None = None,
    ) -> list[TextDetection]:
        resized, scale = self._resize_for_max_side(image_bgr, self.max_side)
        scaled_regions = self._scale_regions(excluded_regions or [], scale)
        masked = self._mask_regions(resized, scaled_regions)
        texts = self._filter_detections_by_excluded_regions(
            self.ocr_engine.recognize(masked),
            scaled_regions,
        )
        if scale == 1.0:
            return texts
        return [
            replace(text, box=self._scale_box(text.box, 1.0 / scale))
            for text in texts
        ]

    @staticmethod
    def _resize_for_max_side(image_bgr: BgrImage, max_side: int) -> tuple[BgrImage, float]:
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

    @staticmethod
    def _scale_box(box: tuple[int, int, int, int], scale: float) -> tuple[int, int, int, int]:
        x1, y1, x2, y2 = box
        return (
            int(round(x1 * scale)),
            int(round(y1 * scale)),
            int(round(x2 * scale)),
            int(round(y2 * scale)),
        )

    @classmethod
    def _scale_regions(
        cls,
        regions: list[tuple[int, int, int, int]],
        scale: float,
    ) -> list[tuple[int, int, int, int]]:
        if scale == 1.0:
            return [region for region in regions if cls._valid_box(region)]
        scaled_regions = [cls._scale_box(region, scale) for region in regions]
        return [region for region in scaled_regions if cls._valid_box(region)]

    @staticmethod
    def _mask_regions(
        image_bgr: BgrImage,
        regions: list[tuple[int, int, int, int]],
    ) -> BgrImage:
        if not regions:
            return image_bgr
        masked = image_bgr.copy()
        for x1, y1, x2, y2 in regions:
            masked[y1:y2, x1:x2] = 0
        return cast(BgrImage, masked)

    @classmethod
    def _filter_detections_by_excluded_regions(
        cls,
        detections: list[DetectionT],
        regions: list[tuple[int, int, int, int]],
    ) -> list[DetectionT]:
        if not regions:
            return detections
        kept: list[DetectionT] = []
        for detection in detections:
            if not cls._box_overlaps_excluded_regions(detection.box, regions):
                kept.append(detection)
        return kept

    @classmethod
    def _box_overlaps_excluded_regions(
        cls,
        box: tuple[int, int, int, int],
        regions: list[tuple[int, int, int, int]],
    ) -> bool:
        center_x = (box[0] + box[2]) / 2.0
        center_y = (box[1] + box[3]) / 2.0
        box_area = cls._box_area(box)
        for region in regions:
            if region[0] <= center_x <= region[2] and region[1] <= center_y <= region[3]:
                return True
            if box_area <= 0:
                continue
            overlap = cls._intersection_area(box, region)
            if overlap / box_area >= 0.5:
                return True
        return False

    @staticmethod
    def _intersection_area(
        a: tuple[int, int, int, int],
        b: tuple[int, int, int, int],
    ) -> int:
        left = max(a[0], b[0])
        top = max(a[1], b[1])
        right = min(a[2], b[2])
        bottom = min(a[3], b[3])
        if right <= left or bottom <= top:
            return 0
        return (right - left) * (bottom - top)

    @staticmethod
    def _box_area(box: tuple[int, int, int, int]) -> int:
        return max(0, box[2] - box[0]) * max(0, box[3] - box[1])

    @staticmethod
    def _valid_box(box: tuple[int, int, int, int]) -> bool:
        return box[2] > box[0] and box[3] > box[1]
