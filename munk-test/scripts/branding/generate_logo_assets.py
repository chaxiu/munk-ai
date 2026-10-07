#!/usr/bin/env python3
"""Generate website logo assets from a single source image.

This script is designed for the Munk AI repository. It creates:

- transparent PNG logo marks for UI usage
- ICO favicon bundles for browser tabs
- optional solid-background JPG variants for square icon use
- a JSON manifest describing every generated file

The source image is expected to have a mostly uniform background.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

try:
    from PIL import Image, ImageFilter, ImageOps
except ImportError as exc:  # pragma: no cover - dependency guidance path
    raise SystemExit(
        "This script requires Pillow. Install it with:\n"
        "  python3 -m pip install Pillow"
    ) from exc


RGBColor = tuple[int, int, int]
RGBAColor = tuple[int, int, int, int]

DEFAULT_INPUT = Path("logo/Munk-AI-logo.jpg")
DEFAULT_OUTPUT_ROOT = Path("logo/generated")


@dataclass(frozen=True)
class ExportSpec:
    filename: str
    size: int
    purpose: str
    background: str
    fmt: str = "PNG"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate logo assets for munk-web and web-ui.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Source image path.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Directory to store generated assets.",
    )
    parser.add_argument(
        "--background-threshold",
        type=int,
        default=28,
        help="RGB distance threshold for detecting the uniform source background.",
    )
    parser.add_argument(
        "--edge-sample-width",
        type=int,
        default=24,
        help="How many edge pixels to sample when estimating the source background color.",
    )
    parser.add_argument(
        "--padding-ratio",
        type=float,
        default=0.14,
        help="Inner padding ratio for exported square assets.",
    )
    parser.add_argument(
        "--solid-background",
        default="#F3E6D0",
        help="Solid background color for square non-transparent exports.",
    )
    parser.add_argument(
        "--skip-jpg",
        action="store_true",
        help="Do not export optional solid-background JPG assets.",
    )
    return parser.parse_args()


def parse_hex_color(value: str) -> RGBColor:
    text = value.strip().lstrip("#")
    if len(text) != 6:
        raise ValueError(f"Expected 6 hex digits, got {value!r}")
    return tuple(int(text[index : index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]


def relative_output_path(base: Path, path: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def sample_edge_pixels(image: Image.Image, sample_width: int) -> list[RGBColor]:
    rgb_image = image.convert("RGB")
    width, height = rgb_image.size
    band = max(1, min(sample_width, width // 4 or 1, height // 4 or 1))
    pixels = cast(Any, rgb_image.load())
    samples: list[RGBColor] = []

    for x in range(width):
        for y in range(band):
            samples.append(pixels[x, y])
            samples.append(pixels[x, height - 1 - y])
    for y in range(height):
        for x in range(band):
            samples.append(pixels[x, y])
            samples.append(pixels[width - 1 - x, y])
    return samples


def median_color(samples: list[RGBColor]) -> RGBColor:
    if not samples:
        raise ValueError("No pixels available for background estimation.")
    channels = list(zip(*samples))
    return tuple(sorted(channel)[len(channel) // 2] for channel in channels)  # type: ignore[return-value]


def rgb_distance_sq(left: RGBColor, right: RGBColor) -> int:
    return sum((int(left[index]) - int(right[index])) ** 2 for index in range(3))


def build_alpha_mask(
    image: Image.Image,
    background_color: RGBColor,
    threshold: int,
) -> Image.Image:
    rgb_image = image.convert("RGB")
    width, height = rgb_image.size
    threshold_sq = threshold * threshold
    pixels = cast(Any, rgb_image.load())

    background_candidate = [[False] * width for _ in range(height)]
    for y in range(height):
        row = background_candidate[y]
        for x in range(width):
            row[x] = rgb_distance_sq(pixels[x, y], background_color) <= threshold_sq

    queue: list[tuple[int, int]] = []
    visited = [[False] * width for _ in range(height)]

    def try_push(x: int, y: int) -> None:
        if visited[y][x] or not background_candidate[y][x]:
            return
        visited[y][x] = True
        queue.append((x, y))

    for x in range(width):
        try_push(x, 0)
        try_push(x, height - 1)
    for y in range(height):
        try_push(0, y)
        try_push(width - 1, y)

    index = 0
    while index < len(queue):
        x, y = queue[index]
        index += 1
        if x > 0:
            try_push(x - 1, y)
        if x + 1 < width:
            try_push(x + 1, y)
        if y > 0:
            try_push(x, y - 1)
        if y + 1 < height:
            try_push(x, y + 1)

    alpha = Image.new("L", (width, height), color=255)
    alpha_pixels = cast(Any, alpha.load())
    for y in range(height):
        for x in range(width):
            if visited[y][x]:
                alpha_pixels[x, y] = 0

    return alpha.filter(ImageFilter.GaussianBlur(radius=1.2))


def apply_alpha_mask(image: Image.Image, alpha_mask: Image.Image) -> Image.Image:
    rgba_image = image.convert("RGBA")
    rgba_image.putalpha(alpha_mask)
    return rgba_image


def crop_visible_content(image: Image.Image, alpha_cutoff: int = 8) -> Image.Image:
    alpha_channel = image.getchannel("A")
    threshold_map = [0 if value <= alpha_cutoff else 255 for value in range(256)]
    visible_mask = cast(Image.Image, alpha_channel.point(threshold_map))
    bbox = visible_mask.getbbox()
    if bbox is None:
        return image.copy()
    return image.crop(bbox)


def make_square_logo(
    image: Image.Image,
    size: int,
    padding_ratio: float,
    background: RGBAColor,
) -> Image.Image:
    if image.mode != "RGBA":
        raise ValueError("Expected RGBA image for square export.")

    inner_size = max(1, round(size * (1.0 - 2.0 * padding_ratio)))
    scaled = ImageOps.contain(image, (inner_size, inner_size), method=Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), background)
    offset = ((size - scaled.width) // 2, (size - scaled.height) // 2)
    canvas.alpha_composite(scaled, dest=offset)
    return canvas


def optimize_png_image(image: Image.Image) -> Image.Image:
    if "A" in image.getbands():
        return image
    adaptive = image.convert("P", palette=Image.Palette.ADAPTIVE, colors=256)
    return adaptive


def save_png(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    candidate = optimize_png_image(image)
    candidate.save(path, format="PNG", optimize=True, compress_level=9)


def save_ico(base_image: Image.Image, path: Path, sizes: list[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    base_image.save(path, format="ICO", sizes=[(size, size) for size in sizes])


def save_jpg(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rgb = image.convert("RGB")
    rgb.save(
        path,
        format="JPEG",
        quality=84,
        optimize=True,
        progressive=True,
        subsampling=2,
    )


def write_manifest(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_specs() -> dict[str, list[ExportSpec]]:
    return {
        "munk-web": [
            ExportSpec("favicon-16.png", 16, "browser favicon", "transparent"),
            ExportSpec("favicon-32.png", 32, "browser favicon", "transparent"),
            ExportSpec("favicon-48.png", 48, "search/favicon fallback", "transparent"),
            ExportSpec("apple-touch-icon.png", 180, "iOS home screen icon", "solid"),
            ExportSpec("icon-192.png", 192, "PWA icon", "solid"),
            ExportSpec("icon-512.png", 512, "PWA icon", "solid"),
            ExportSpec("logo-mark-64.png", 64, "small brand mark", "transparent"),
            ExportSpec("logo-mark-128.png", 128, "brand mark", "transparent"),
            ExportSpec("logo-mark-256.png", 256, "brand mark", "transparent"),
        ],
        "web-ui": [
            ExportSpec("favicon-16.png", 16, "browser favicon", "transparent"),
            ExportSpec("favicon-32.png", 32, "browser favicon", "transparent"),
            ExportSpec("logo-ui-20.png", 20, "dense UI header mark", "transparent"),
            ExportSpec("logo-ui-24.png", 24, "compact UI header mark", "transparent"),
            ExportSpec("logo-ui-32.png", 32, "standard UI mark", "transparent"),
            ExportSpec("logo-ui-40.png", 40, "touch-friendly UI mark", "transparent"),
            ExportSpec("logo-ui-64.png", 64, "high-density UI mark", "transparent"),
        ],
    }


def generate_assets(
    source_path: Path,
    output_root: Path,
    threshold: int,
    edge_sample_width: int,
    padding_ratio: float,
    solid_background_rgb: RGBColor,
    skip_jpg: bool,
) -> dict[str, Any]:
    source_image = Image.open(source_path)
    background_samples = sample_edge_pixels(source_image, edge_sample_width)
    background_color = median_color(background_samples)
    alpha_mask = build_alpha_mask(source_image, background_color, threshold)
    transparent_logo = crop_visible_content(apply_alpha_mask(source_image, alpha_mask))

    specs_by_site = build_specs()
    manifest: dict[str, Any] = {
        "source": str(source_path),
        "background_estimation": {
            "estimated_rgb": list(background_color),
            "threshold": threshold,
            "edge_sample_width": edge_sample_width,
        },
        "padding_ratio": padding_ratio,
        "outputs": {},
    }

    solid_background_rgba: RGBAColor = (*solid_background_rgb, 255)
    transparent_background: RGBAColor = (0, 0, 0, 0)

    preview_transparent = make_square_logo(
        transparent_logo,
        size=512,
        padding_ratio=padding_ratio,
        background=transparent_background,
    )
    preview_solid = make_square_logo(
        transparent_logo,
        size=512,
        padding_ratio=padding_ratio,
        background=solid_background_rgba,
    )
    save_png(preview_transparent, output_root / "shared" / "source-transparent-512.png")
    save_png(preview_solid, output_root / "shared" / "source-solid-512.png")

    for site_name, specs in specs_by_site.items():
        site_root = output_root / site_name
        generated: list[dict[str, Any]] = []
        favicon_base = None

        for spec in specs:
            background = transparent_background if spec.background == "transparent" else solid_background_rgba
            exported = make_square_logo(
                transparent_logo,
                size=spec.size,
                padding_ratio=padding_ratio,
                background=background,
            )
            output_path = site_root / spec.filename
            save_png(exported, output_path)
            generated.append(
                {
                    "filename": spec.filename,
                    "format": spec.fmt,
                    "size": spec.size,
                    "purpose": spec.purpose,
                    "background": spec.background,
                    "path": relative_output_path(output_root, output_path),
                }
            )
            if spec.filename == "favicon-32.png":
                favicon_base = exported

        if favicon_base is None:
            raise ValueError(f"Missing favicon base for {site_name}")

        ico_path = site_root / "favicon.ico"
        save_ico(
            make_square_logo(
                transparent_logo,
                size=256,
                padding_ratio=padding_ratio,
                background=transparent_background,
            ),
            ico_path,
            sizes=[16, 32, 48],
        )
        generated.append(
            {
                "filename": "favicon.ico",
                "format": "ICO",
                "size": [16, 32, 48],
                "purpose": "browser favicon bundle",
                "background": "transparent",
                "path": relative_output_path(output_root, ico_path),
            }
        )

        if not skip_jpg:
            jpg_name = "logo-card-512.jpg" if site_name == "munk-web" else "logo-card-ui-512.jpg"
            jpg_path = site_root / jpg_name
            save_jpg(preview_solid, jpg_path)
            generated.append(
                {
                    "filename": jpg_name,
                    "format": "JPEG",
                    "size": 512,
                    "purpose": "solid square preview asset",
                    "background": "solid",
                    "path": relative_output_path(output_root, jpg_path),
                }
            )

        manifest["outputs"][site_name] = generated

    return manifest


def main() -> int:
    args = parse_args()
    source_path = args.input.resolve()
    output_root = args.output_root.resolve()

    if not source_path.exists():
        print(f"Source image does not exist: {source_path}", file=sys.stderr)
        return 1

    try:
        solid_background = parse_hex_color(args.solid_background)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    output_root.mkdir(parents=True, exist_ok=True)
    manifest = generate_assets(
        source_path=source_path,
        output_root=output_root,
        threshold=args.background_threshold,
        edge_sample_width=args.edge_sample_width,
        padding_ratio=args.padding_ratio,
        solid_background_rgb=solid_background,
        skip_jpg=args.skip_jpg,
    )
    manifest_path = output_root / "manifest.json"
    write_manifest(manifest_path, manifest)

    print(f"Generated logo assets in: {output_root}")
    print(f"Manifest: {manifest_path}")
    for site_name, entries in manifest["outputs"].items():
        print(f"- {site_name}: {len(entries)} files")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
