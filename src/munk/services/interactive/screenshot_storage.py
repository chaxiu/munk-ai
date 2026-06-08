from __future__ import annotations

from pathlib import Path

from munk.user_data import runs_home

__all__ = ["write_interactive_screenshot"]


def write_interactive_screenshot(
    *,
    session_id: str,
    captured_at: str,
    image_bytes: bytes,
) -> Path:
    screenshots_dir = runs_home() / "interactive" / session_id / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"observe_{_sanitize_timestamp(captured_at)}.png"
    path = screenshots_dir / file_name
    path.write_bytes(image_bytes)
    return path.resolve()


def _sanitize_timestamp(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value)
