from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ResolvedPerceptionAssets:
    icon_model_path: Path | None = None
    det_model_path: Path | None = None
    det_config_path: Path | None = None
    rec_model_path: Path | None = None
    rec_yaml_path: Path | None = None
    rec_keys_path: Path | None = None
    cls_model_path: Path | None = None

    def required_paths(self) -> tuple[Path, ...]:
        return tuple(
            path
            for path in (
                self.icon_model_path,
                self.det_model_path,
                self.det_config_path,
                self.rec_model_path,
                self.rec_yaml_path,
                self.rec_keys_path,
                self.cls_model_path,
            )
            if path is not None
        )

    def named_paths(self) -> dict[str, Path]:
        mapping = {
            "icon_model_path": self.icon_model_path,
            "det_model_path": self.det_model_path,
            "det_config_path": self.det_config_path,
            "rec_model_path": self.rec_model_path,
            "rec_yaml_path": self.rec_yaml_path,
            "rec_keys_path": self.rec_keys_path,
            "cls_model_path": self.cls_model_path,
        }
        return {name: path for name, path in mapping.items() if path is not None}


@dataclass(frozen=True)
class PerceptionAssetBundle:
    provider_name: str
    asset_root: Path | None
    assets: ResolvedPerceptionAssets
