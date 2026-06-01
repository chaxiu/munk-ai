from __future__ import annotations


class PerceptionProviderError(LookupError):
    """Base error for perception provider discovery failures."""


class PerceptionProviderNotFoundError(PerceptionProviderError):
    """Raised when a requested perception provider is not installed."""


class PerceptionProviderConflictError(PerceptionProviderError):
    """Raised when multiple providers are installed but none is selected."""


class PerceptionProviderUnavailableError(PerceptionProviderError):
    """Raised when no perception provider is installed."""
