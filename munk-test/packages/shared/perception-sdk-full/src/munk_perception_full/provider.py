from __future__ import annotations

from pathlib import Path

from munk.perception.contracts import (
    PerceptionAnalyzeRequest,
    PerceptionAnalyzeResult,
    PerceptionProviderFactory,
)
from munk.perception.diagnostics import PerceptionProviderDiagnostics
from munk.perception.resources import PerceptionAssetBundle

from .annotate import annotate_image
from .assets import diagnose_assets, resolve_asset_bundle
from .engine import PerceptionEngine
from .screen_graph_builder import build_observed_screen_frame
from .tree_registry import parse_observation_tree


class FullPerceptionProvider:
    def __init__(
        self,
        *,
        asset_bundle: PerceptionAssetBundle,
        max_side: int = 1600,
        icon_conf: float = 0.12,
        engine: PerceptionEngine | None = None,
    ) -> None:
        self.provider_name = "full"
        self._asset_bundle = asset_bundle
        self._default_icon_conf = icon_conf
        assets = asset_bundle.assets
        self._engine = engine or PerceptionEngine(
            icon_model_path=_required_path(assets.icon_model_path, "icon_model_path"),
            det_model_path=_required_path(assets.det_model_path, "det_model_path"),
            det_config_path=_required_path(assets.det_config_path, "det_config_path"),
            rec_model_path=_required_path(assets.rec_model_path, "rec_model_path"),
            rec_yaml_path=_required_path(assets.rec_yaml_path, "rec_yaml_path"),
            rec_keys_path=_required_path(assets.rec_keys_path, "rec_keys_path"),
            cls_model_path=_required_path(assets.cls_model_path, "cls_model_path"),
            max_side=max_side,
            icon_conf=icon_conf,
        )

    @property
    def asset_bundle(self) -> PerceptionAssetBundle:
        return self._asset_bundle

    def analyze_image(
        self,
        image_bgr,
        *,
        icon_conf: float | None = None,
    ):
        return self._engine.analyze(image_bgr, icon_conf=icon_conf)

    def annotate_image(
        self,
        image_bgr,
        elements,
        *,
        annotate_text: bool = True,
    ):
        return annotate_image(image_bgr, elements, annotate_text=annotate_text)

    def analyze_text(
        self,
        image_bgr,
        *,
        excluded_regions=None,
    ):
        return self._engine.analyze_text(
            image_bgr,
            excluded_regions=excluded_regions,
        )

    def analyze_observation(self, request: PerceptionAnalyzeRequest) -> PerceptionAnalyzeResult:
        observation_tree = request.observation_tree
        tree_available = observation_tree is not None
        tree_error: str | None = None
        tree_nodes = []
        if observation_tree is not None:
            try:
                tree_nodes = parse_observation_tree(
                    observation_tree,
                    screen_size=request.screen_size,
                    current_app_identity=request.current_app_identity,
                )
            except KeyError:
                tree_error = "unsupported_tree_source"
            except Exception as exc:  # noqa: BLE001
                tree_error = str(exc)
                tree_nodes = []
        elements = self._engine.analyze(
            request.image_bgr,
            icon_conf=request.icon_conf if request.icon_conf is not None else self._default_icon_conf,
            excluded_regions=[request.keyboard_bounds] if request.keyboard_bounds is not None else None,
        )
        elements, screen_frame = build_observed_screen_frame(
            entry_identity=request.current_app_identity,
            screen_size=request.screen_size,
            elements=elements,
            tree_nodes=tree_nodes,
            tree_available=tree_available,
            tree_error=tree_error,
            keyboard_visible=request.keyboard_visible,
            keyboard_bounds=request.keyboard_bounds,
            keyboard_source=request.keyboard_source,
        )
        return PerceptionAnalyzeResult(
            elements=elements,
            screen_frame=screen_frame,
            observation_tree=observation_tree,
            tree_available=tree_available,
            tree_error=tree_error,
        )


class FullPerceptionProviderFactory(PerceptionProviderFactory):
    provider_name = "full"

    def create_provider(
        self,
        *,
        max_side: int = 1600,
        icon_conf: float = 0.12,
        cache_dir: Path | None = None,
        options: dict[str, str] | None = None,
    ) -> FullPerceptionProvider:
        return FullPerceptionProvider(
            asset_bundle=self.describe_assets(cache_dir=cache_dir, options=options),
            max_side=max_side,
            icon_conf=icon_conf,
        )

    def describe_assets(
        self,
        *,
        cache_dir: Path | None = None,
        options: dict[str, str] | None = None,
    ) -> PerceptionAssetBundle:
        return resolve_asset_bundle(cache_dir=cache_dir, options=options)

    def diagnose(
        self,
        *,
        cache_dir: Path | None = None,
        options: dict[str, str] | None = None,
    ) -> PerceptionProviderDiagnostics:
        return diagnose_assets(cache_dir=cache_dir, options=options)


def build_provider_factory() -> FullPerceptionProviderFactory:
    return FullPerceptionProviderFactory()


def _required_path(path: Path | None, label: str) -> Path:
    if path is None:
        raise FileNotFoundError(f"missing perception asset: {label}")
    return path
