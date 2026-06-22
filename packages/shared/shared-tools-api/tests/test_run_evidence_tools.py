from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Callable, cast

from munk.shared_tools.run_evidence import register_run_evidence_tools
from pydantic_ai import Agent


@dataclass
class _Provider:
    calls: list[tuple[int | None, bool]] = field(default_factory=list)

    def read_step_summary(self, step_index: int) -> str:
        return f"summary:{step_index}"

    def read_step_screen(self, step_index: int) -> str:
        return f"screen:{step_index}"

    def read_step_transition(self, step_index: int) -> str:
        return f"transition:{step_index}"

    def read_step_screenshot(self, step_index: int | None = None, annotated: bool = True) -> str:
        self.calls.append((step_index, annotated))
        return f"screenshot:{step_index}:{annotated}"


def test_register_run_evidence_tools_exposes_screenshot_with_raw_mode() -> None:
    agent: Agent[object, str] = Agent(model="test", output_type=str, defer_model_check=True)
    register_run_evidence_tools(agent, provider_getter=lambda deps: deps.provider)
    tools = agent._function_toolset.tools
    provider = _Provider()
    deps = SimpleNamespace(provider=provider)

    read_step_screenshot = cast(Callable[..., str], tools["read_step_screenshot"].function)

    annotated_result = read_step_screenshot(SimpleNamespace(deps=deps), step_index=None, annotated=True)
    raw_result = read_step_screenshot(SimpleNamespace(deps=deps), step_index=3, annotated=False)

    assert "read_step_screen_raw_image" not in tools
    assert annotated_result == "screenshot:None:True"
    assert raw_result == "screenshot:3:False"
    assert provider.calls == [(None, True), (3, False)]
