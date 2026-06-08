from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from munk.agent_base.output_strategy import resolve_output_strategy
from munk.agent_base.pydantic_model_factory import build_pydantic_ai_model
from munk.optimizing.models import OptimizeFieldPatch, OptimizeRequest, OptimizeResult

from munk.config import resolve_role_model_config

from .agent import PydanticAiOptimizeAgent
from .tools import OptimizeToolDeps


def _load_json(path_value: str | None) -> object:
    if not path_value:
        return None
    path = Path(path_value)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


class OptimizeRuntimeService:
    def __init__(self, *, resolved_config: Any) -> None:
        optimize_config = resolve_role_model_config(resolved_config.config, role="optimize")
        if optimize_config is None:
            raise ValueError("config must include a valid optimize model configuration")
        model = build_pydantic_ai_model(optimize_config, config=resolved_config.config)
        self._agent = PydanticAiOptimizeAgent(
            model=model,
            output_strategy=resolve_output_strategy(optimize_config),
        )

    def optimize(self, request: OptimizeRequest) -> OptimizeResult:
        artifact_payloads = dict(request.artifact_payloads)
        attempts = artifact_payloads.get("attempts")
        if not isinstance(attempts, list):
            attempts = _load_json(request.artifacts.get("attempts"))
        history = artifact_payloads.get("history")
        if not isinstance(history, list):
            history = _load_json(request.artifacts.get("history"))
        retry_handoffs = artifact_payloads.get("retry_handoffs")
        if not isinstance(retry_handoffs, list):
            retry_handoffs = _load_json(request.artifacts.get("retry_handoffs"))
        judge_result = artifact_payloads.get("judge_result")
        if judge_result is None:
            judge_result = _load_json(request.artifacts.get("judge_result"))
        decision_trace = artifact_payloads.get("decision_trace")
        if decision_trace is None:
            decision_trace = _load_json(request.artifacts.get("decision_trace"))
        step_summaries = _build_step_summaries(attempts)
        step_screens = _build_indexed_payload(_load_json(request.artifacts.get("observation_frames")))
        step_transitions = _build_indexed_payload(_load_json(request.artifacts.get("observation_diffs")))
        request_for_agent = request.model_copy(
            update={
                "artifact_payloads": {
                    **artifact_payloads,
                    "attempts": attempts if isinstance(attempts, list) else [],
                    "history": history if isinstance(history, list) else [],
                    "retry_handoffs": retry_handoffs if isinstance(retry_handoffs, list) else [],
                    "judge_result": judge_result,
                    "decision_trace": decision_trace if isinstance(decision_trace, list) else [],
                }
            }
        )
        deps = OptimizeToolDeps(
            request=request_for_agent,
            step_summaries=step_summaries,
            step_screens=step_screens,
            step_transitions=step_transitions,
            step_images=_build_step_images(request.artifacts.get("raw_screenshots")),
        )
        output = self._agent.optimize(request_for_agent, deps=deps)
        return OptimizeResult(
            summary=output.summary,
            patched_fields=[
                OptimizeFieldPatch(
                    field_name=item.field_name,
                    replace_with=list(item.replace_with),
                    reason=item.reason,
                )
                for item in output.patched_fields
            ],
            artifacts={"tool_calls": json.dumps(deps.tool_calls, ensure_ascii=False)},
        )


def _build_step_summaries(attempts: object) -> dict[int, dict[str, object]]:
    indexed: dict[int, dict[str, object]] = {}
    if not isinstance(attempts, list):
        return indexed
    for attempt in attempts:
        if not isinstance(attempt, dict):
            continue
        runner = attempt.get("runner")
        if not isinstance(runner, dict):
            continue
        event_history = runner.get("event_history")
        if not isinstance(event_history, list):
            continue
        for step_index, event in enumerate(event_history):
            if isinstance(event, dict):
                indexed.setdefault(step_index, dict(event))
    return indexed


def _build_indexed_payload(raw_items: object) -> dict[int, dict[str, object]]:
    indexed: dict[int, dict[str, object]] = {}
    if not isinstance(raw_items, list):
        return indexed
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        step_index = item.get("step_index")
        if isinstance(step_index, int):
            indexed[step_index] = dict(item)
    return indexed


def _build_step_images(raw_screenshot_dir: str | None) -> dict[int, str]:
    indexed: dict[int, str] = {}
    if not raw_screenshot_dir:
        return indexed
    root = Path(raw_screenshot_dir)
    if not root.exists() or not root.is_dir():
        return indexed
    for child in sorted(root.iterdir()):
        if not child.is_file():
            continue
        digits = "".join(character for character in child.stem if character.isdigit())
        if not digits:
            continue
        indexed[int(digits)] = str(child)
    return indexed
