from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from pydantic_ai import Agent
from pydantic_ai import RunContext as PydanticRunContext
from pydantic_ai.messages import ToolReturn


class RunEvidenceToolProvider(Protocol):
    def read_step_summary(self, step_index: int) -> str: ...

    def read_step_screen(self, step_index: int) -> str: ...

    def read_step_transition(self, step_index: int) -> str: ...

    def read_step_screen_raw_image(self, step_index: int) -> str | ToolReturn: ...


def register_run_evidence_tools(
    agent: Agent[Any, Any],
    *,
    provider_getter: Callable[[Any], RunEvidenceToolProvider],
) -> None:
    @agent.tool
    def read_step_summary(ctx: PydanticRunContext[Any], step_index: int) -> str:
        """Read a bounded summary for a single step."""
        return provider_getter(ctx.deps).read_step_summary(step_index)

    @agent.tool
    def read_step_screen(ctx: PydanticRunContext[Any], step_index: int) -> str:
        """Read bounded screen-state details for a single step."""
        return provider_getter(ctx.deps).read_step_screen(step_index)

    @agent.tool
    def read_step_transition(ctx: PydanticRunContext[Any], step_index: int) -> str:
        """Read bounded transition details for a single step."""
        return provider_getter(ctx.deps).read_step_transition(step_index)

    @agent.tool
    def read_step_screen_raw_image(ctx: PydanticRunContext[Any], step_index: int) -> str | ToolReturn:
        """Read the compressed raw screenshot image for a single step."""
        return provider_getter(ctx.deps).read_step_screen_raw_image(step_index)
