from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


def empty_raw_payload() -> dict[str, Any]:
    return {}


@dataclass(frozen=True)
class WDAAppState:
    bundle_id: str | None
    surface_identity: str | None = None
    title: str | None = None
    raw: dict[str, Any] = field(default_factory=empty_raw_payload)


@dataclass(frozen=True)
class WDAAccessibilityTree:
    payload: dict[str, Any]


class WDAProvider(Protocol):
    def ensure_session(self) -> None: ...

    def screenshot_png(self) -> bytes: ...

    def tap(self, x: int, y: int) -> None: ...

    def long_press(self, x: int, y: int, duration_sec: float | None = None) -> None: ...

    def swipe(
        self,
        *,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration_sec: float | None = None,
    ) -> None: ...

    def type_text(self, text: str) -> None: ...

    def clear_text(self) -> None: ...

    def press(self, key: str) -> None: ...

    def dismiss_soft_keyboard(self) -> None: ...

    def current_app(self) -> WDAAppState: ...

    def window_size(self) -> tuple[int, int]: ...

    def accessibility_tree(self) -> WDAAccessibilityTree | None: ...

    def launch_app(self, bundle_id: str) -> None: ...

    def terminate_app(self, bundle_id: str) -> None: ...

    def close(self) -> None: ...
