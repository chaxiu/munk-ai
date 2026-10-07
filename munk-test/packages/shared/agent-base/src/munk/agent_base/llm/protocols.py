from __future__ import annotations

from typing import Protocol


class VisionCompleter(Protocol):
    def complete_vision(self, *, system: str | None, user: str, image_png_bytes: bytes) -> str:
        """Return model text for one annotated screenshot (PNG bytes) plus prompt text."""
        ...
