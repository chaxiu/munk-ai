from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Literal, Protocol

from pydantic_ai import Agent
from pydantic_ai import RunContext as PydanticRunContext

AiGuidanceFieldName = Literal[
    "objective_clarifications",
    "preflight_checks",
    "interaction_hints",
    "disambiguation_rules",
    "recovery_hints",
    "judge_hints",
]
AI_GUIDANCE_FIELDS: tuple[AiGuidanceFieldName, ...] = (
    "objective_clarifications",
    "preflight_checks",
    "interaction_hints",
    "disambiguation_rules",
    "recovery_hints",
    "judge_hints",
)
FIELD_DESCRIPTIONS: dict[AiGuidanceFieldName, str] = {
    "objective_clarifications": "implicit intent constraints and clarifications",
    "preflight_checks": "preconditions to verify before interaction",
    "interaction_hints": "interaction guidance for the runner",
    "disambiguation_rules": "rules for distinguishing similar UI states",
    "recovery_hints": "recovery guidance after confusion or failed interaction",
    "judge_hints": "judge-side pass/fail interpretation hints",
}


class AiGuidanceToolProvider(Protocol):
    def non_empty_fields(self) -> list[AiGuidanceFieldName]: ...

    def read_fields(self, fields: list[AiGuidanceFieldName]) -> dict[str, list[str]]: ...

    def read_all(self) -> dict[str, list[str]]: ...


def register_ai_guidance_tools(
    agent: Agent[Any, Any],
    *,
    provider_getter: Callable[[Any], AiGuidanceToolProvider],
    recorder: Callable[[str, dict[str, object], str], str] | None = None,
) -> None:
    def _maybe_record(tool_name: str, arguments: dict[str, object], payload: str) -> str:
        if recorder is None:
            return payload
        return recorder(tool_name, arguments, payload)

    @agent.tool
    def list_ai_guidance_fields(ctx: PydanticRunContext[Any]) -> str:
        """List allowed ai_guidance fields and which ones are currently non-empty."""
        provider = provider_getter(ctx.deps)
        payload = json.dumps(
            {
                "fields": [
                    {
                        "field_name": field_name,
                        "description": FIELD_DESCRIPTIONS[field_name],
                        "has_content": field_name in provider.non_empty_fields(),
                    }
                    for field_name in AI_GUIDANCE_FIELDS
                ]
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        return _maybe_record("list_ai_guidance_fields", {}, payload)

    @agent.tool
    def read_ai_guidance_fields(ctx: PydanticRunContext[Any], fields: list[AiGuidanceFieldName]) -> str:
        """Read one or more selected ai_guidance fields."""
        provider = provider_getter(ctx.deps)
        payload = json.dumps(
            {"fields": provider.read_fields(list(dict.fromkeys(fields)))},
            ensure_ascii=False,
            sort_keys=True,
        )
        return _maybe_record("read_ai_guidance_fields", {"fields": list(fields)}, payload)

    @agent.tool
    def read_all_ai_guidance(ctx: PydanticRunContext[Any]) -> str:
        """Read all non-empty ai_guidance fields."""
        provider = provider_getter(ctx.deps)
        payload = json.dumps({"fields": provider.read_all()}, ensure_ascii=False, sort_keys=True)
        return _maybe_record("read_all_ai_guidance", {}, payload)
