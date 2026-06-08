from __future__ import annotations


class RecordingRuntimeError(RuntimeError):
    """Base error for recording runtime resolution and execution."""


class RecordingRuntimeUnavailableError(RecordingRuntimeError, LookupError):
    """Raised when no recording runtime is installed."""


class RecordingRuntimeConflictError(RecordingRuntimeError, LookupError):
    """Raised when multiple recording runtimes are installed without selection."""


class RecordingSessionNotFoundError(RecordingRuntimeError):
    """Raised when a recording session cannot be found."""


class RecordingSessionStateError(RecordingRuntimeError):
    """Raised when an invalid session lifecycle transition is requested."""


class RecordingInteractionContractError(RecordingRuntimeError, ValueError):
    """Raised when a recording interaction and its forwarding ack are inconsistent."""
