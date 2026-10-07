from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path
from typing import Any, cast

import yaml

_DEFAULT_SOURCE_DIR = (
    Path(__file__).resolve().parents[1]
    / "models"
    / "PP-OCRv5_mobile_det_safetensors"
)
_DEFAULT_OUTPUT_DIR = (
    Path(__file__).resolve().parents[1]
    / "packages"
    / "shared"
    / "perception-sdk-full"
    / "src"
    / "munk_perception_full"
    / "resources"
    / "vision-core"
)
_DEFAULT_DOWNLOAD_URL = (
    "https://paddle-model-ecology.bj.bcebos.com/paddlex/"
    "official_inference_model/paddle3.0.0/PP-OCRv5_mobile_det_infer.tar"
)
_DEFAULT_ONNX_FILENAME = "vision_det_a.onnx"
_DEFAULT_CONFIG_FILENAME = "vision_det_a.json"
_MODEL_CANDIDATES = ("inference.pdmodel", "inference.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert the official PP-OCRv5 mobile detection inference model to ONNX "
            "and materialize the RapidOCR-side preprocessing/postprocessing config."
        )
    )
    parser.add_argument(
        "--source-dir",
        default=str(_DEFAULT_SOURCE_DIR),
        help="Directory containing the downloaded PP-OCRv5_mobile_det_safetensors metadata.",
    )
    parser.add_argument(
        "--paddle-infer-dir",
        default=None,
        help=(
            "Optional directory containing the official Paddle inference files "
            "(inference.pdmodel or inference.json, inference.pdiparams, inference.yml). "
            "If omitted, the script downloads the official inference tarball."
        ),
    )
    parser.add_argument(
        "--download-url",
        default=_DEFAULT_DOWNLOAD_URL,
        help="Official Paddle inference tarball URL used when --paddle-infer-dir is omitted.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(_DEFAULT_OUTPUT_DIR),
        help="Directory to place the generated ONNX file and RapidOCR config.",
    )
    parser.add_argument(
        "--onnx-filename",
        default=_DEFAULT_ONNX_FILENAME,
        help="Output ONNX filename.",
    )
    parser.add_argument(
        "--config-filename",
        default=_DEFAULT_CONFIG_FILENAME,
        help="Output RapidOCR config filename.",
    )
    parser.add_argument(
        "--opset",
        type=int,
        default=19,
        help="ONNX opset version passed to paddle2onnx.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _ensure_export_dependencies()

    source_dir = Path(args.source_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    onnx_path = output_dir / args.onnx_filename
    config_path = output_dir / args.config_filename

    if not source_dir.exists():
        raise FileNotFoundError(f"missing mobile det metadata directory: {source_dir}")

    rapidocr_config = build_rapidocr_config(source_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.paddle_infer_dir:
        infer_dir = resolve_infer_dir(Path(args.paddle_infer_dir).expanduser().resolve())
        convert_to_onnx(infer_dir=infer_dir, output_path=onnx_path, opset=args.opset)
    else:
        with tempfile.TemporaryDirectory(prefix="munk-ppocr-mobile-det-") as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            tar_path = temp_dir / "PP-OCRv5_mobile_det_infer.tar"
            download_file(args.download_url, tar_path)
            infer_dir = extract_infer_dir(tar_path, temp_dir / "extracted")
            convert_to_onnx(infer_dir=infer_dir, output_path=onnx_path, opset=args.opset)

    config_path.write_text(json.dumps(rapidocr_config, indent=2) + "\n", encoding="utf-8")

    print(f"generated onnx: {onnx_path}")
    print(f"generated rapidocr config: {config_path}")
    print("you can now point the perception provider det model to these files.")
    return 0


def build_rapidocr_config(source_dir: Path) -> dict[str, Any]:
    preprocessor = _read_json(source_dir / "preprocessor_config.json")
    inference = _read_yaml(source_dir / "inference.yml")

    post_raw = inference.get("PostProcess")
    post = cast(dict[str, object], post_raw) if isinstance(post_raw, dict) else {}
    mean = preprocessor.get("image_mean")
    std = preprocessor.get("image_std")
    limit_side_len = preprocessor.get("limit_side_len")

    if not isinstance(mean, list) or len(mean) != 3:
        raise ValueError("preprocessor_config.json missing image_mean")
    if not isinstance(std, list) or len(std) != 3:
        raise ValueError("preprocessor_config.json missing image_std")
    if not isinstance(limit_side_len, int):
        raise ValueError("preprocessor_config.json missing integer limit_side_len")
    mean_values = [_float_or_default(value, 0.0) for value in cast(list[object], mean)]
    std_values = [_float_or_default(value, 0.0) for value in cast(list[object], std)]

    return {
        "model_name": "vision_det_a",
        "limit_side_len": limit_side_len,
        "limit_type": "max",
        "mean": mean_values,
        "std": std_values,
        "thresh": _float_or_default(post.get("thresh"), 0.3),
        "box_thresh": _float_or_default(post.get("box_thresh"), 0.6),
        "unclip_ratio": _float_or_default(post.get("unclip_ratio"), 1.5),
    }


def resolve_infer_dir(path: Path) -> Path:
    if path.is_file():
        raise ValueError(f"--paddle-infer-dir must be a directory, got file: {path}")
    if _contains_supported_infer_files(path):
        return path
    for child in path.iterdir():
        if child.is_dir() and _contains_supported_infer_files(child):
            return child
    raise FileNotFoundError(
        "could not find a supported Paddle inference bundle "
        f"({', '.join(_MODEL_CANDIDATES)} + inference.pdiparams) under {path}"
    )


def download_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as response, destination.open("wb") as file_obj:
        file_obj.write(response.read())


def extract_infer_dir(tar_path: Path, extract_root: Path) -> Path:
    extract_root.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tar_path, "r:*") as archive:
        archive.extractall(extract_root)
    return resolve_infer_dir(extract_root)


def convert_to_onnx(*, infer_dir: Path, output_path: Path, opset: int) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    model_filename = resolve_model_filename(infer_dir)
    command = [
        sys.executable,
        "-m",
        "paddle2onnx.command",
        "--model_dir",
        str(infer_dir),
        "--model_filename",
        model_filename,
        "--params_filename",
        "inference.pdiparams",
        "--save_file",
        str(output_path),
        "--opset_version",
        str(opset),
    ]
    subprocess.run(command, check=True)


def resolve_model_filename(infer_dir: Path) -> str:
    for candidate in _MODEL_CANDIDATES:
        if (infer_dir / candidate).exists():
            return candidate
    raise FileNotFoundError(
        f"missing Paddle model file in {infer_dir}; expected one of: {', '.join(_MODEL_CANDIDATES)}"
    )


def _contains_supported_infer_files(path: Path) -> bool:
    return (path / "inference.pdiparams").exists() and any(
        (path / candidate).exists() for candidate in _MODEL_CANDIDATES
    )


def _ensure_export_dependencies() -> None:
    missing: list[str] = []
    if importlib.util.find_spec("paddle2onnx") is None:
        missing.append("paddle2onnx")
    if importlib.util.find_spec("paddle") is None:
        missing.append("paddlepaddle")
    if not missing:
        return
    install_hints = {
        "paddle2onnx": "python -m pip install paddle2onnx",
        "paddlepaddle": "python -m pip install paddlepaddle",
    }
    hint_text = "; ".join(install_hints[name] for name in missing)
    raise ModuleNotFoundError(
        "missing export dependencies: "
        + ", ".join(missing)
        + ". Install them first with: "
        + hint_text
    )


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected mapping json: {path}")
    return cast(dict[str, Any], data)


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected mapping yaml: {path}")
    return cast(dict[str, Any], data)


def _float_or_default(value: object, default: float) -> float:
    if value is None:
        return default
    if not isinstance(value, int | float | str):
        raise ValueError(f"expected float-compatible value, got: {value!r}")
    return float(value)


if __name__ == "__main__":
    raise SystemExit(main())
