from __future__ import annotations

import os
from pathlib import Path

import yaml
from munk.perception.diagnostics import PerceptionProviderDiagnostics
from munk.perception.resources import PerceptionAssetBundle, ResolvedPerceptionAssets

_PROVIDER_NAME = "full"
_ENV_RESOURCE_ROOT = "MUNK_PERCEPTION_RESOURCE_ROOT"
_OCR_RESOURCE_DIRNAME = "vision-core"
_KEYS_FILENAME = "vision_rec_a.keys.txt"
_DET_MODEL_FILENAME = "vision_det_a.onnx"
_DET_CONFIG_FILENAME = "vision_det_a.json"
_REC_MODEL_FILENAME = "vision_rec_a.onnx"
_REC_CONFIG_FILENAME = "vision_rec_a.yml"
_CLS_MODEL_FILENAME = "vision_cls_a.onnx"
_ICON_MODEL_RELATIVE_PATH = Path("models") / "detect" / "detect.onnx"


def resolve_asset_bundle(
    *,
    cache_dir: Path | None = None,
    options: dict[str, str] | None = None,
) -> PerceptionAssetBundle:
    asset_root = _resolve_asset_root(options)
    keys_root = _resolve_keys_root(cache_dir)
    assets = ResolvedPerceptionAssets(
        icon_model_path=_optional_path(asset_root / _ICON_MODEL_RELATIVE_PATH),
        det_model_path=_optional_path(asset_root / _OCR_RESOURCE_DIRNAME / _DET_MODEL_FILENAME),
        det_config_path=_optional_path(asset_root / _OCR_RESOURCE_DIRNAME / _DET_CONFIG_FILENAME),
        rec_model_path=_optional_path(asset_root / _OCR_RESOURCE_DIRNAME / _REC_MODEL_FILENAME),
        rec_yaml_path=_optional_path(asset_root / _OCR_RESOURCE_DIRNAME / _REC_CONFIG_FILENAME),
        rec_keys_path=_resolve_rec_keys_path(asset_root, keys_root),
        cls_model_path=_optional_path(asset_root / _OCR_RESOURCE_DIRNAME / _CLS_MODEL_FILENAME),
    )
    return PerceptionAssetBundle(provider_name=_PROVIDER_NAME, asset_root=asset_root, assets=assets)


def diagnose_assets(
    *,
    cache_dir: Path | None = None,
    options: dict[str, str] | None = None,
) -> PerceptionProviderDiagnostics:
    bundle = resolve_asset_bundle(cache_dir=cache_dir, options=options)
    missing_items: list[str] = []
    for name, path in bundle.assets.named_paths().items():
        if not path.exists():
            missing_items.append(f"{name} missing: {path}")
    for name in (
        "icon_model_path",
        "det_model_path",
        "det_config_path",
        "rec_model_path",
        "rec_yaml_path",
        "rec_keys_path",
        "cls_model_path",
    ):
        if getattr(bundle.assets, name) is None:
            missing_items.append(f"{name} missing")
    details = {
        name: str(path)
        for name, path in bundle.assets.named_paths().items()
    }
    details["icon_model_expected_format"] = "onnx"
    return PerceptionProviderDiagnostics(
        provider_name=_PROVIDER_NAME,
        asset_root=bundle.asset_root,
        details=details,
        missing_items=missing_items,
    )


def _resolve_asset_root(options: dict[str, str] | None) -> Path:
    if options is not None and options.get("resource_root"):
        return Path(options["resource_root"]).expanduser().resolve()
    if os.environ.get(_ENV_RESOURCE_ROOT):
        return Path(os.environ[_ENV_RESOURCE_ROOT]).expanduser().resolve()
    return Path(__file__).resolve().parent / "resources"


def _resolve_keys_root(cache_dir: Path | None) -> Path:
    if cache_dir is None:
        cache_dir = Path.home() / ".cache" / "munk" / "perception-full"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _resolve_rec_keys_path(asset_root: Path, keys_root: Path) -> Path | None:
    packaged = asset_root / _OCR_RESOURCE_DIRNAME / _KEYS_FILENAME
    if packaged.exists():
        return packaged
    yaml_path = asset_root / _OCR_RESOURCE_DIRNAME / _REC_CONFIG_FILENAME
    if not yaml_path.exists():
        return None
    materialized = keys_root / _KEYS_FILENAME
    if materialized.exists():
        return materialized
    config = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    charset = config["PostProcess"]["character_dict"]
    materialized.write_text("\n".join(charset) + "\n", encoding="utf-8")
    return materialized


def _optional_path(path: Path) -> Path | None:
    return path
