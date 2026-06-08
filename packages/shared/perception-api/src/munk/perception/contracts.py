from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol

from .diagnostics import PerceptionProviderDiagnostics
from .image import BgrImage
from .resources import PerceptionAssetBundle
from .screen_graph import ObservedScreenFrame
from .types import ClickableElement, TextDetection


@dataclass(frozen=True)
class ObservationTree:
    source_type: Literal["android_uixml", "ios_ax_tree", "web_dom"]
    content_type: Literal["xml", "json", "html"]
    payload: str


@dataclass(frozen=True)
class PerceptionAnalyzeRequest:
    image_bgr: BgrImage
    screen_size: tuple[int, int]
    current_app_identity: str | None = None
    observation_tree: ObservationTree | None = None
    icon_conf: float | None = None
    keyboard_visible: bool | None = None
    keyboard_bounds: tuple[int, int, int, int] | None = None
    keyboard_source: str | None = None


@dataclass(frozen=True)
class PerceptionAnalyzeResult:
    elements: list[ClickableElement]
    screen_frame: ObservedScreenFrame
    observation_tree: ObservationTree | None
    tree_available: bool
    tree_error: str | None = None


@dataclass(frozen=True)
class PerceptionRuntimeConfig:
    provider: str | None = None
    cache_dir: Path | None = None
    extra_options: dict[str, str] = field(default_factory=dict)


class PerceptionProvider(Protocol):
    provider_name: str

    def analyze_image(
        self,
        image_bgr: BgrImage,
        *,
        icon_conf: float | None = None,
    ) -> list[ClickableElement]: ...

    def annotate_image(
        self,
        image_bgr: BgrImage,
        elements: list[ClickableElement],
        *,
        annotate_text: bool = True,
    ) -> BgrImage: ...

    def analyze_text(
        self,
        image_bgr: BgrImage,
        *,
        excluded_regions: list[tuple[int, int, int, int]] | None = None,
    ) -> list[TextDetection]: ...

    def analyze_observation(self, request: PerceptionAnalyzeRequest) -> PerceptionAnalyzeResult: ...


class PerceptionProviderFactory(Protocol):
    provider_name: str

    def create_provider(
        self,
        *,
        max_side: int = 1600,
        icon_conf: float = 0.12,
        cache_dir: Path | None = None,
        options: dict[str, str] | None = None,
    ) -> PerceptionProvider: ...

    def describe_assets(
        self,
        *,
        cache_dir: Path | None = None,
        options: dict[str, str] | None = None,
    ) -> PerceptionAssetBundle: ...

    def diagnose(
        self,
        *,
        cache_dir: Path | None = None,
        options: dict[str, str] | None = None,
    ) -> PerceptionProviderDiagnostics: ...
