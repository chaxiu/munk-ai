from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

import numpy as np
import numpy.typing as npt
import yaml

try:
    from rapidocr import RapidOCR
except ModuleNotFoundError as exc:
    raise ModuleNotFoundError(
        "RapidOCR is required for OCR. Install it into the current Python "
        "environment with `python -m pip install rapidocr`."
    ) from exc

from munk.perception.types import TextDetection

QuadPoints = npt.NDArray[np.float32] | list[list[float]] | list[tuple[float, float]]


@dataclass(frozen=True)
class DetRuntimeConfig:
    limit_side_len: int | None = None
    limit_type: str | None = None
    mean: tuple[float, float, float] | None = None
    std: tuple[float, float, float] | None = None
    thresh: float | None = None
    box_thresh: float | None = None
    unclip_ratio: float | None = None


class RapidOcrResult(Protocol):
    boxes: Sequence[QuadPoints] | None
    txts: Sequence[str] | None
    scores: Sequence[float] | None


class OcrEngine:
    def __init__(
        self,
        det_model_path: Path,
        det_config_path: Path | None,
        rec_model_path: Path,
        rec_yaml_path: Path,
        rec_keys_path: Path,
        cls_model_path: Path,
        det_target_long_side: int | None = None,
        det_db_thresh: float | None = None,
        det_box_thresh: float | None = None,
        det_unclip_ratio: float | None = None,
        rec_score_thresh: float = 0.72,
    ) -> None:
        det_config = self._load_det_runtime_config(det_config_path)
        self.det_target_long_side = (
            det_target_long_side if det_target_long_side is not None else det_config.limit_side_len or 1440
        )
        self.det_db_thresh = det_db_thresh if det_db_thresh is not None else det_config.thresh or 0.3
        self.det_box_thresh = det_box_thresh if det_box_thresh is not None else det_config.box_thresh or 0.6
        self.det_unclip_ratio = (
            det_unclip_ratio if det_unclip_ratio is not None else det_config.unclip_ratio or 1.3
        )
        self.rec_score_thresh = rec_score_thresh
        self.engine = RapidOCR(
            params=self._build_rapidocr_params(
                det_model_path=det_model_path,
                det_config=det_config,
                rec_model_path=rec_model_path,
                rec_yaml_path=rec_yaml_path,
                rec_keys_path=rec_keys_path,
                cls_model_path=cls_model_path,
                det_target_long_side=self.det_target_long_side,
                det_db_thresh=self.det_db_thresh,
                det_box_thresh=self.det_box_thresh,
                det_unclip_ratio=self.det_unclip_ratio,
            )
        )

    def recognize(self, image_bgr: npt.NDArray[np.uint8]) -> list[TextDetection]:
        results: list[TextDetection] = []
        output = cast(
            RapidOcrResult,
            self.engine(
                image_bgr,
                use_cls=False,
                text_score=self.rec_score_thresh,
                box_thresh=self.det_box_thresh,
                unclip_ratio=self.det_unclip_ratio,
            ),
        )
        if output.boxes is None or output.txts is None or output.scores is None:
            return results

        for box_points, text, score in zip(output.boxes, output.txts, output.scores):
            score_value = float(score)
            if not self._should_keep_text(text, score_value):
                continue
            image_shape: tuple[int, int] = (int(image_bgr.shape[0]), int(image_bgr.shape[1]))
            box = self._quad_to_box(box_points, image_shape)
            if box is None:
                continue
            results.append(TextDetection(box, text.strip(), score_value))
        return results

    def _should_keep_text(self, text: str, score: float) -> bool:
        cleaned = text.strip()
        if not cleaned:
            return False
        if score < self.rec_score_thresh:
            return False
        if self._looks_like_ascii_noise(cleaned):
            return False
        return True

    @staticmethod
    def _looks_like_ascii_noise(text: str) -> bool:
        ascii_letters = [ch for ch in text if ch.isascii() and ch.isalpha()]
        if len(ascii_letters) < 6 or len(ascii_letters) != len(text):
            return False
        transitions = 0
        for prev, current in zip(text, text[1:]):
            if prev.islower() != current.islower():
                transitions += 1
        return transitions >= 3

    @staticmethod
    def _build_rapidocr_params(
        det_model_path: Path,
        det_config: DetRuntimeConfig,
        rec_model_path: Path,
        rec_yaml_path: Path,
        rec_keys_path: Path,
        cls_model_path: Path,
        det_target_long_side: int,
        det_db_thresh: float,
        det_box_thresh: float,
        det_unclip_ratio: float,
    ) -> dict[str, object]:
        if not cls_model_path.exists():
            raise FileNotFoundError(
                f"RapidOCR requires a local cls model at {cls_model_path}. "
                "Please place the ONNX file there to avoid runtime downloads."
            )
        if not rec_keys_path.exists():
            raise FileNotFoundError(f"RapidOCR rec keys file missing: {rec_keys_path}")
        limit_side_len = det_target_long_side if det_target_long_side > 0 else 2000
        return {
            "Global.use_cls": False,
            "Global.model_root_dir": str(det_model_path.parent),
            "Global.max_side_len": limit_side_len,
            "Det.model_path": str(det_model_path),
            "Det.limit_side_len": limit_side_len,
            "Det.limit_type": det_config.limit_type or "max",
            "Det.mean": list(det_config.mean or (0.5, 0.5, 0.5)),
            "Det.std": list(det_config.std or (0.5, 0.5, 0.5)),
            "Det.thresh": det_db_thresh,
            "Det.box_thresh": det_box_thresh,
            "Det.unclip_ratio": det_unclip_ratio,
            "Cls.model_path": str(cls_model_path),
            "Rec.model_path": str(rec_model_path),
            "Rec.rec_keys_path": str(rec_keys_path),
        }

    @staticmethod
    def _load_det_runtime_config(path: Path | None) -> DetRuntimeConfig:
        if path is None:
            return DetRuntimeConfig()
        if not path.exists():
            raise FileNotFoundError(f"RapidOCR det config missing: {path}")
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            return DetRuntimeConfig(
                limit_side_len=_as_int(data.get("limit_side_len")),
                limit_type=_as_limit_type(data.get("limit_type")),
                mean=_as_triplet(data.get("mean")),
                std=_as_triplet(data.get("std")),
                thresh=_as_float(data.get("thresh")),
                box_thresh=_as_float(data.get("box_thresh")),
                unclip_ratio=_as_float(data.get("unclip_ratio")),
            )

        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"expected mapping det config: {path}")
        return DetRuntimeConfig(
            limit_side_len=_extract_yaml_resize_long(data),
            limit_type="max",
            thresh=_as_float((data.get("PostProcess") or {}).get("thresh")),
            box_thresh=_as_float((data.get("PostProcess") or {}).get("box_thresh")),
            unclip_ratio=_as_float((data.get("PostProcess") or {}).get("unclip_ratio")),
        )

    @staticmethod
    def _clip_box(
        box: tuple[int, int, int, int],
        shape: tuple[int, int],
    ) -> tuple[int, int, int, int]:
        height, width = shape
        x1, y1, x2, y2 = box
        x1 = max(0, min(width - 1, x1))
        y1 = max(0, min(height - 1, y1))
        x2 = max(0, min(width - 1, x2))
        y2 = max(0, min(height - 1, y2))
        if x2 <= x1:
            x2 = min(width - 1, x1 + 1)
        if y2 <= y1:
            y2 = min(height - 1, y1 + 1)
        return x1, y1, x2, y2

    @staticmethod
    def _quad_to_box(
        points: QuadPoints,
        shape: tuple[int, int],
    ) -> tuple[int, int, int, int] | None:
        array = np.asarray(points, dtype=np.float32)
        if array.size == 0 or array.ndim != 2 or array.shape[1] != 2:
            return None
        x1 = int(np.floor(array[:, 0].min()))
        y1 = int(np.floor(array[:, 1].min()))
        x2 = int(np.ceil(array[:, 0].max()))
        y2 = int(np.ceil(array[:, 1].max()))
        return OcrEngine._clip_box((x1, y1, x2, y2), shape)


def _as_float(value: object) -> float | None:
    if value is None:
        return None
    if not isinstance(value, int | float | str):
        raise ValueError(f"expected float-compatible value, got: {value!r}")
    return float(value)


def _as_int(value: object) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int | float | str):
        raise ValueError(f"expected int-compatible value, got: {value!r}")
    return int(value)


def _as_limit_type(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    if text not in {"min", "max"}:
        raise ValueError(f"unsupported det limit_type: {text}")
    return text


def _as_triplet(value: object) -> tuple[float, float, float] | None:
    if value is None:
        return None
    if not isinstance(value, Sequence) or len(value) != 3:
        raise ValueError(f"expected 3 values, got: {value!r}")
    return (float(value[0]), float(value[1]), float(value[2]))


def _extract_yaml_resize_long(data: dict[str, object]) -> int | None:
    preprocess = data.get("PreProcess")
    if not isinstance(preprocess, dict):
        return None
    preprocess_mapping = cast(dict[str, object], preprocess)
    transform_ops = preprocess_mapping.get("transform_ops")
    if not isinstance(transform_ops, list):
        return None
    for op in transform_ops:
        if not isinstance(op, dict):
            continue
        op_mapping = cast(dict[str, object], op)
        resize = op_mapping.get("DetResizeForTest")
        if isinstance(resize, dict) and resize.get("resize_long") is not None:
            resize_long = resize["resize_long"]
            if not isinstance(resize_long, int | float | str):
                raise ValueError(f"unsupported resize_long value: {resize_long!r}")
            return int(resize_long)
    return None
