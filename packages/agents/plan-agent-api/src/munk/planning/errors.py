from __future__ import annotations


class PlanRuntimeError(RuntimeError):
    """Base error for plan runtime resolution and execution."""


class PlanRuntimeUnavailableError(PlanRuntimeError, LookupError):
    """Raised when no plan runtime is installed."""


class PlanRuntimeConflictError(PlanRuntimeError, LookupError):
    """Raised when multiple plan runtimes are installed without selection."""
