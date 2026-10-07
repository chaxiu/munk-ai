from __future__ import annotations


class OperationCancelledError(RuntimeError):
    """Raised when review execution is cooperatively cancelled."""
