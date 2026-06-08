from __future__ import annotations

from pathlib import Path
from typing import cast

import cv2
import numpy as np
import numpy.typing as npt
import onnxruntime as ort
from munk.perception.image import BgrImage
from munk.perception.types import IconDetection

from .geometry import nms
from .image_io import letterbox

FloatArray = npt.NDArray[np.float32]


class IconDetector:
    def __init__(
        self,
        model_path: Path,
        input_size: int = 1280,
        conf_threshold: float = 0.12,
        iou_threshold: float = 0.3,
    ) -> None:
        self.model_path = model_path
        providers = cast(list[str], ort.get_available_providers())
        if "CUDAExecutionProvider" in providers:
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        else:
            providers = ["CPUExecutionProvider"]
        self.session = _load_model_session(model_path, providers)
        self.input_name = self.session.get_inputs()[0].name
        self.input_size = input_size
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold

    def detect(
        self,
        image_bgr: BgrImage,
        conf_threshold: float | None = None,
    ) -> list[IconDetection]:
        target_size = self.input_size
        image_rgb = cast(BgrImage, cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB))
        padded, scale, pad = letterbox(image_rgb, target_size)
        padded_f32 = cast(FloatArray, padded.astype(np.float32) / np.float32(255.0))
        blob = cast(FloatArray, np.transpose(padded_f32, (2, 0, 1))[None, :, :, :])
        output = cast(FloatArray, self.session.run(None, {self.input_name: blob})[0])
        if output.ndim == 3:
            output = cast(FloatArray, output[0])
        if output.shape[0] < output.shape[1]:
            output = cast(FloatArray, output.transpose(1, 0))
        boxes, scores = self._parse_output(output)
        if boxes.size == 0:
            return []
        keep = nms(boxes, scores, self.iou_threshold)

        def _collect(threshold: float) -> list[IconDetection]:
            results: list[IconDetection] = []
            image_shape: tuple[int, int] = (int(image_bgr.shape[0]), int(image_bgr.shape[1]))
            for idx in keep:
                if scores[idx] < threshold:
                    continue
                x1, y1, x2, y2 = boxes[idx]
                x1 = (x1 - pad[0]) / scale
                y1 = (y1 - pad[1]) / scale
                x2 = (x2 - pad[0]) / scale
                y2 = (y2 - pad[1]) / scale
                x1, y1, x2, y2 = self._clip_box((x1, y1, x2, y2), image_shape)
                results.append(IconDetection((x1, y1, x2, y2), float(scores[idx])))
            return results

        applied_threshold = self.conf_threshold if conf_threshold is None else float(conf_threshold)
        thresholds = [applied_threshold, 0.12, 0.10, 0.08]
        thresholds = sorted({t for t in thresholds if t <= applied_threshold}, reverse=True)
        if not thresholds:
            thresholds = [applied_threshold]
        min_icons = min(4, len(keep))
        detections: list[IconDetection] = []
        for threshold in thresholds:
            detections = _collect(threshold)
            if len(detections) >= min_icons or threshold == thresholds[-1]:
                break
        return detections

    def _parse_output(self, output: FloatArray) -> tuple[FloatArray, FloatArray]:
        if output.shape[1] == 6:
            boxes = output[:, :4]
            scores = output[:, 4]
        elif output.shape[1] > 6:
            obj = output[:, 4]
            cls_scores = output[:, 5:]
            scores = obj * cls_scores.max(axis=1)
            boxes = output[:, :4]
        else:
            boxes = output[:, :4]
            scores = (
                output[:, 4]
                if output.shape[1] > 4
                else np.zeros((output.shape[0],), dtype=np.float32)
            )
        boxes_xyxy = np.zeros_like(boxes, dtype=np.float32)
        boxes_xyxy[:, 0] = boxes[:, 0] - boxes[:, 2] / 2.0
        boxes_xyxy[:, 1] = boxes[:, 1] - boxes[:, 3] / 2.0
        boxes_xyxy[:, 2] = boxes[:, 0] + boxes[:, 2] / 2.0
        boxes_xyxy[:, 3] = boxes[:, 1] + boxes[:, 3] / 2.0
        return cast(FloatArray, boxes_xyxy), cast(FloatArray, scores)

    @staticmethod
    def _clip_box(
        box: tuple[float, float, float, float],
        shape: tuple[int, int],
    ) -> tuple[int, int, int, int]:
        height, width = shape
        x1, y1, x2, y2 = box
        x1 = max(0, min(width - 1, int(round(x1))))
        y1 = max(0, min(height - 1, int(round(y1))))
        x2 = max(0, min(width - 1, int(round(x2))))
        y2 = max(0, min(height - 1, int(round(y2))))
        return x1, y1, x2, y2


def _load_model_session(
    model_path: Path,
    providers: list[str],
) -> ort.InferenceSession:
    return ort.InferenceSession(str(model_path), providers=providers)
