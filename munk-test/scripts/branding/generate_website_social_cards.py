#!/usr/bin/env python3
"""Generate branded social card images for the website."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as exc:  # pragma: no cover - dependency guidance path
    raise SystemExit(
        "This script requires Pillow. Install it with:\n"
        "  python3 -m pip install Pillow"
    ) from exc


WIDTH = 1200
HEIGHT = 630


@dataclass(frozen=True)
class CardSpec:
    filename: str
    eyebrow: str
    title_lines: tuple[str, ...]
    body_lines: tuple[str, ...]
    panel_lines: tuple[str, ...]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate OG/Twitter social card images for munk-web.")
    parser.add_argument(
        "--logo",
        type=Path,
        default=Path("munk-web/public/brand/logo-mark-256.png"),
        help="Transparent brand logo PNG path.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("munk-web/public/og"),
        help="Directory for generated social card files.",
    )
    return parser.parse_args()


def load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = []
    if bold:
        candidates.extend(
            [
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/Library/Fonts/Arial Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            ]
        )
    else:
        candidates.extend(
            [
                "/System/Library/Fonts/Supplemental/Arial.ttf",
                "/Library/Fonts/Arial.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            ]
        )

    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def draw_brand_header(draw: ImageDraw.ImageDraw, canvas: Image.Image, logo: Image.Image) -> None:
    pill_box = (80, 72, 390, 136)
    draw.rounded_rectangle(pill_box, radius=18, fill="#ffffff", outline="#d0d7de", width=2)

    logo_resized = logo.resize((40, 40), Image.Resampling.LANCZOS)
    canvas.alpha_composite(logo_resized, dest=(104, 84))

    label_font = load_font(28, bold=True)
    draw.text((156, 88), "Munk AI", font=label_font, fill="#24292f")


def draw_text_block(draw: ImageDraw.ImageDraw, spec: CardSpec) -> None:
    eyebrow_font = load_font(24, bold=True)
    title_font = load_font(58, bold=True)
    body_font = load_font(28)

    draw.text((96, 180), spec.eyebrow, font=eyebrow_font, fill="#57606a")

    y = 240
    for line in spec.title_lines:
        draw.text((96, y), line, font=title_font, fill="#24292f")
        y += 68

    y += 28
    for line in spec.body_lines:
        draw.text((96, y), line, font=body_font, fill="#57606a")
        y += 40


def draw_runtime_panel(draw: ImageDraw.ImageDraw, canvas: Image.Image, logo: Image.Image, spec: CardSpec) -> None:
    panel_box = (640, 120, 1092, 510)
    draw.rounded_rectangle(panel_box, radius=24, fill="#0d1117")
    draw.rounded_rectangle(panel_box, radius=24, outline="#30363d", width=2)
    draw.rounded_rectangle((672, 154, 1060, 214), radius=14, fill="#161b22")

    logo_badge = logo.resize((28, 28), Image.Resampling.LANCZOS)
    canvas.alpha_composite(logo_badge, dest=(690, 170))

    panel_label_font = load_font(24, bold=True)
    panel_line_font = load_font(24)
    caption_font = load_font(22)

    draw.text((730, 170), "Runtime", font=panel_label_font, fill="#c9d1d9")
    draw.text((680, 238), "Local-first verification stack", font=caption_font, fill="#8b949e")

    y = 290
    for line in spec.panel_lines:
        draw.text((680, y), line, font=panel_line_font, fill="#c9d1d9")
        y += 52


def build_card(spec: CardSpec, logo_path: Path, output_path: Path) -> None:
    logo = Image.open(logo_path).convert("RGBA")
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), "#ffffff")
    draw = ImageDraw.Draw(canvas)

    draw.rounded_rectangle((60, 60, 1140, 570), radius=28, fill="#ffffff", outline="#d0d7de", width=2)
    draw.rectangle((61, 61, 1139, 220), fill="#ffffff")
    draw_brand_header(draw, canvas, logo)
    draw_text_block(draw, spec)
    draw_runtime_panel(draw, canvas, logo, spec)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(
        output_path,
        format="JPEG",
        quality=88,
        optimize=True,
        progressive=True,
        subsampling=2,
    )


def main() -> int:
    args = parse_args()
    logo_path = args.logo.resolve()
    output_dir = args.output_dir.resolve()

    if not logo_path.exists():
        print(f"Logo file does not exist: {logo_path}", file=sys.stderr)
        return 1

    specs = [
        CardSpec(
            filename="default-card.jpg",
            eyebrow="Local-first AI testing",
            title_lines=("Verify real product", "changes with Munk AI"),
            body_lines=("Execution, review-first verification, and recording", "in one local-first runtime for developers and agents."),
            panel_lines=("CLI / Local API / MCP", "planner / runner / judge", "review runtime", "recording runtime + web"),
        ),
        CardSpec(
            filename="home-card.jpg",
            eyebrow="Homepage",
            title_lines=("Test real product", "changes locally."),
            body_lines=("A practical runtime for developers and coding agents", "working on execution, verification, and recording."),
            panel_lines=("serve / plan / run plan", "review / verify change", "interactive device MCP", "recording web + sidecar"),
        ),
    ]

    for spec in specs:
        build_card(spec, logo_path=logo_path, output_path=output_dir / spec.filename)

    print(f"Generated social cards in: {output_dir}")
    for spec in specs:
        print(f"- {spec.filename}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
