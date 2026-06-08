from __future__ import annotations


class OptimizeRuntimeError(RuntimeError):
    """Base error for optimize runtime resolution and execution."""


class OptimizeRuntimeUnavailableError(OptimizeRuntimeError, LookupError):
    """Raised when no optimize runtime is installed."""


class OptimizeRuntimeConflictError(OptimizeRuntimeError, LookupError):
    """Raised when multiple optimize runtimes are installed without selection."""
