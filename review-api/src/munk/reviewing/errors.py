from __future__ import annotations


class ReviewRuntimeError(RuntimeError):
    """Base error for review runtime resolution and execution."""


class ReviewRuntimeUnavailableError(ReviewRuntimeError, LookupError):
    """Raised when no review runtime is installed."""


class ReviewRuntimeConflictError(ReviewRuntimeError, LookupError):
    """Raised when multiple review runtimes are installed without selection."""
