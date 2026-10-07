from __future__ import annotations


class JudgeRuntimeError(RuntimeError):
    """Base error for judge runtime resolution and execution."""


class JudgeRuntimeUnavailableError(JudgeRuntimeError, LookupError):
    """Raised when no judge runtime is installed."""


class JudgeRuntimeConflictError(JudgeRuntimeError, LookupError):
    """Raised when multiple judge runtimes are installed without selection."""
