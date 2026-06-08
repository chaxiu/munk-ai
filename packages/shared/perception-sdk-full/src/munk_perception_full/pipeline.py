from __future__ import annotations

from pathlib import Path

import cv2
from munk.perception.image import BgrImage
from munk.perception.types import ClickableElement

from .annotate import annotate_image
from .fusion import fuse_elements
from .icon import IconDetector
from .image_io import load_image_bgr
from .ocr import OcrEngine


def run_perception(
    image_path: Path,
    output_path: Path,
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
) -> tuple[list[ClickableElement], Path]:
    image_bgr, _ = load_image_bgr(image_path, max_side=max_side)
    icon_detector = IconDetector(icon_model_path, input_size=1280, conf_threshold=icon_conf)
    ocr_engine = OcrEngine(
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
    icons = icon_detector.detect(image_bgr)
    texts = ocr_engine.recognize(image_bgr)
    elements = fuse_elements(icons, texts)
    annotated = annotate_image(image_bgr, elements)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), annotated)
    return elements, output_path


def run_perception_on_image(
    image_bgr: BgrImage,
    icon_model_path: Path,
    det_model_path: Path,
    det_config_path: Path | None,
    rec_model_path: Path,
    rec_yaml_path: Path,
    rec_keys_path: Path,
    cls_model_path: Path,
    icon_conf: float = 0.12,
    ocr_det_target_long_side: int | None = None,
    ocr_det_db_thresh: float | None = None,
    ocr_det_box_thresh: float | None = None,
    ocr_det_unclip_ratio: float | None = None,
    ocr_rec_score_thresh: float = 0.72,
) -> list[ClickableElement]:
    icon_detector = IconDetector(icon_model_path, input_size=1280, conf_threshold=icon_conf)
    ocr_engine = OcrEngine(
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
    icons = icon_detector.detect(image_bgr)
    texts = ocr_engine.recognize(image_bgr)
    elements = fuse_elements(icons, texts)
    return elements
