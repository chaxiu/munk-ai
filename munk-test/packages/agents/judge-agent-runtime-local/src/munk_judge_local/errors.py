from __future__ import annotations


class OperationCancelledError(RuntimeError):
    """Raised when judge execution is cooperatively cancelled."""
