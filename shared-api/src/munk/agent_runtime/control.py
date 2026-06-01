from typing import Protocol


class CancelController(Protocol):
    def is_cancel_requested(self) -> bool: ...


__all__ = ["CancelController"]
