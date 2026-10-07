from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path
from typing import Any, cast

import yaml

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
    "official_inference_model/paddle3.0.0/PP-OCRv5_mobile_rec_infer.tar"
)
_DEFAULT_ONNX_FILENAME = "vision_rec_a.onnx"
_DEFAULT_CONFIG_FILENAME = "vision_rec_a.yml"
_DEFAULT_KEYS_FILENAME = "vision_rec_a.keys.txt"
_MODEL_CANDIDATES = ("inference.pdmodel", "inference.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert the official PP-OCRv5 mobile recognition inference model to ONNX "
            "and materialize the inference.yml / keys files used by the local OCR runtime."
        )
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
        help="Directory to place the generated ONNX file and runtime metadata.",
    )
    parser.add_argument(
        "--onnx-filename",
        default=_DEFAULT_ONNX_FILENAME,
        help="Output ONNX filename.",
    )
    parser.add_argument(
        "--config-filename",
        default=_DEFAULT_CONFIG_FILENAME,
        help="Output inference YAML filename.",
    )
    parser.add_argument(
        "--keys-filename",
        default=_DEFAULT_KEYS_FILENAME,
        help="Output recognition keys filename.",
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

    output_dir = Path(args.output_dir).expanduser().resolve()
    onnx_path = output_dir / args.onnx_filename
    config_path = output_dir / args.config_filename
    keys_path = output_dir / args.keys_filename

    output_dir.mkdir(parents=True, exist_ok=True)

    if args.paddle_infer_dir:
        infer_dir = resolve_infer_dir(Path(args.paddle_infer_dir).expanduser().resolve())
        export_mobile_rec_assets(
            infer_dir=infer_dir,
            onnx_path=onnx_path,
            config_path=config_path,
            keys_path=keys_path,
            opset=args.opset,
        )
    else:
        with tempfile.TemporaryDirectory(prefix="munk-ppocr-mobile-rec-") as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            tar_path = temp_dir / "PP-OCRv5_mobile_rec_infer.tar"
            download_file(args.download_url, tar_path)
            infer_dir = extract_infer_dir(tar_path, temp_dir / "extracted")
            export_mobile_rec_assets(
                infer_dir=infer_dir,
                onnx_path=onnx_path,
                config_path=config_path,
                keys_path=keys_path,
                opset=args.opset,
            )

    print(f"generated onnx: {onnx_path}")
    print(f"generated config: {config_path}")
    print(f"generated keys: {keys_path}")
    return 0


def export_mobile_rec_assets(
    *,
    infer_dir: Path,
    onnx_path: Path,
    config_path: Path,
    keys_path: Path,
    opset: int,
) -> None:
    convert_to_onnx(infer_dir=infer_dir, output_path=onnx_path, opset=opset)
    inference_yml_path = infer_dir / "inference.yml"
    if not inference_yml_path.exists():
        raise FileNotFoundError(f"missing inference.yml in {infer_dir}")
    config = _read_yaml(inference_yml_path)
    _rewrite_runtime_metadata(config)
    config_path.write_text(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    keys_path.write_text(_build_keys_text(config), encoding="utf-8")


def _build_keys_text(config: dict[str, Any]) -> str:
    postprocess = config.get("PostProcess")
    if not isinstance(postprocess, dict):
        raise ValueError("inference.yml missing PostProcess section")
    postprocess_mapping = cast(dict[str, object], postprocess)
    charset = postprocess_mapping.get("character_dict")
    if not isinstance(charset, list):
        raise ValueError("inference.yml missing PostProcess.character_dict")
    charset_values: list[str] = []
    for item in cast(list[object], charset):
        if not isinstance(item, str):
            raise ValueError("inference.yml PostProcess.character_dict must contain only strings")
        charset_values.append(item)
    return "\n".join(charset_values) + "\n"


def _rewrite_runtime_metadata(config: dict[str, Any]) -> None:
    global_config = config.get("Global")
    if not isinstance(global_config, dict):
        return
    global_mapping = cast(dict[str, object], global_config)
    global_mapping["model_name"] = "vision_rec_a"


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


def _read_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected mapping yaml: {path}")
    return cast(dict[str, Any], data)


if __name__ == "__main__":
    raise SystemExit(main())
