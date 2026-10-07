import json
from pathlib import Path

import cv2
from munk_perception_full.assets import resolve_asset_bundle
from munk_perception_full.ocr import OcrEngine

_SMOKE_IMAGE_PATH = Path(__file__).resolve().parent / "fixtures" / "ocr" / "step_0000.png"


def test_build_rapidocr_params_uses_det_runtime_config(tmp_path: Path) -> None:
    det_model_path = tmp_path / "vision_det_a.onnx"
    rec_model_path = tmp_path / "vision_rec_a.onnx"
    rec_yaml_path = tmp_path / "vision_rec_a.yml"
    rec_keys_path = tmp_path / "vision_rec_a.keys.txt"
    cls_model_path = tmp_path / "vision_cls_a.onnx"
    det_config_path = tmp_path / "vision_det_a.json"

    for path in (det_model_path, rec_model_path, rec_yaml_path, rec_keys_path, cls_model_path):
        path.write_text("placeholder", encoding="utf-8")
    det_config_path.write_text(
        json.dumps(
            {
                "limit_side_len": 960,
                "limit_type": "max",
                "mean": [0.406, 0.456, 0.485],
                "std": [0.225, 0.224, 0.229],
                "thresh": 0.3,
                "box_thresh": 0.6,
                "unclip_ratio": 1.5,
            }
        ),
        encoding="utf-8",
    )

    det_config = OcrEngine._load_det_runtime_config(det_config_path)
    params = OcrEngine._build_rapidocr_params(
        det_model_path=det_model_path,
        det_config=det_config,
        rec_model_path=rec_model_path,
        rec_yaml_path=rec_yaml_path,
        rec_keys_path=rec_keys_path,
        cls_model_path=cls_model_path,
        det_target_long_side=960,
        det_db_thresh=0.3,
        det_box_thresh=0.6,
        det_unclip_ratio=1.5,
    )

    assert params["Det.limit_side_len"] == 960
    assert params["Det.limit_type"] == "max"
    assert params["Det.mean"] == [0.406, 0.456, 0.485]
    assert params["Det.std"] == [0.225, 0.224, 0.229]
    assert params["Det.unclip_ratio"] == 1.5


def test_ocr_smoke_with_packaged_assets() -> None:
    image = cv2.imread(str(_SMOKE_IMAGE_PATH))
    assert image is not None

    assets = resolve_asset_bundle().assets
    engine = OcrEngine(
        det_model_path=assets.det_model_path,
        det_config_path=assets.det_config_path,
        rec_model_path=assets.rec_model_path,
        rec_yaml_path=assets.rec_yaml_path,
        rec_keys_path=assets.rec_keys_path,
        cls_model_path=assets.cls_model_path,
    )
    results = engine.recognize(image)
    texts = [item.text for item in results]

    assert len(results) >= 8
    assert any("Tasks" in text for text in texts)
    assert any("Doctor appointment" in text for text in texts)
    assert any("Buy groceries" in text for text in texts)
