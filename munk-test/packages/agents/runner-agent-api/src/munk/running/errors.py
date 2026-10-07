from __future__ import annotations


class RunnerRuntimeError(RuntimeError):
    """Base error for runner runtime resolution and execution."""


class RunnerRuntimeUnavailableError(RunnerRuntimeError, LookupError):
    """Raised when no runner runtime is installed."""


class RunnerRuntimeConflictError(RunnerRuntimeError, LookupError):
    """Raised when multiple runner runtimes are installed without selection."""


class RunnerProtocolError(RuntimeError):
    """Raised when the runner agent violates the terminal tool contract."""

    def __init__(
        self,
        message: str,
        *,
        step_index: int | None = None,
        attempt_count: int = 0,
        last_output_excerpt: str | None = None,
        tool_names_seen: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.step_index = step_index
        self.attempt_count = attempt_count
        self.last_output_excerpt = last_output_excerpt
        self.tool_names_seen = list(tool_names_seen or [])
