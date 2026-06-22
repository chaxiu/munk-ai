from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

from munk.agent_base.llm import llm_transcript_scope
from munk.agent_base.output_strategy import resolve_output_strategy
from munk.agent_base.pydantic_model_factory import build_pydantic_ai_model
from munk.agent_runtime.events import AgentRuntimeEventEmitter
from munk.optimizing.models import OptimizeFieldPatch, OptimizeRequest, OptimizeResult, OptimizeRuntimeContext

from munk.config import resolve_role_model_config

from .agent import PydanticAiOptimizeAgent
from .agent_models import OptimizeAgentOutput
from .tools import OptimizeToolDeps


class OptimizeAgentLike(Protocol):
    last_tool_calls: list[str]
    last_prompt: str

    def optimize(self, request: OptimizeRequest, *, deps: OptimizeToolDeps) -> OptimizeAgentOutput: ...


class OptimizeRuntimeService:
    def __init__(self, *, resolved_config: Any, agent: OptimizeAgentLike | None = None) -> None:
        if agent is not None:
            self._agent = agent
            return
        optimize_config = resolve_role_model_config(resolved_config.config, role="optimize")
        if optimize_config is None:
            raise ValueError("config must include a valid optimize model configuration")
        model = build_pydantic_ai_model(optimize_config, config=resolved_config.config)
        self._agent = agent or PydanticAiOptimizeAgent(
            model=model,
            output_strategy=resolve_output_strategy(optimize_config),
        )

    def optimize(
        self,
        request: OptimizeRequest,
        *,
        context: OptimizeRuntimeContext | None = None,
    ) -> OptimizeResult:
        emitter = AgentRuntimeEventEmitter(
            agent_role="optimize",
            operation_id=context.operation_id if context is not None else None,
            event_sink=context.progress if context is not None else None,
            timeline_scope="child_operation",
            attempt_index=(context.attempt_index if context is not None else request.trigger.source_attempt_index),
            app_id=request.app_id,
            plan_id=request.plan_id,
            case_id=request.case_id,
        )
        emitter.emit_started(
            event_type="optimize_started",
            message="optimize runtime started",
            summary="optimize runtime started",
        )
        structured_evidence = dict(request.structured_evidence) if isinstance(request.structured_evidence, dict) else {}
        raw_attempts = structured_evidence.get("attempts")
        step_summaries = _build_step_summaries(raw_attempts)
        step_screens = _build_indexed_payload(_load_json(request.artifacts.get("observation_frames")))
        step_transitions = _build_indexed_payload(_load_json(request.artifacts.get("observation_diffs")))
        deps = OptimizeToolDeps(
            request=request,
            step_summaries=step_summaries,
            step_screens=step_screens,
            step_transitions=step_transitions,
            step_images=_build_step_images(request.artifacts.get("raw_screenshots")),
            step_annotated_images=_build_step_images(request.artifacts.get("annotated_screenshots")),
        )
        emitter.emit_progress(
            event_type="optimize_evidence_ready",
            message="optimize evidence ready",
            timeline_phase="evidence_ready",
            summary="optimize evidence ready",
            data={
                "attempt_count": len(raw_attempts) if isinstance(raw_attempts, list) else 0,
                "step_summary_count": len(step_summaries),
                "step_screen_count": len(step_screens),
                "step_transition_count": len(step_transitions),
            },
        )
        try:
            output = _run_optimize_agent(self._agent, request=request, deps=deps, context=context)
        except Exception as exc:
            emitter.emit_failed(
                event_type="optimize_failed",
                message="optimize runtime failed",
                summary="optimize runtime failed",
                data={"error_type": exc.__class__.__name__},
            )
            raise
        _write_runtime_artifacts(
            context=context,
            prompt=self._agent.last_prompt,
            tool_calls=self._agent.last_tool_calls,
        )
        for tool_index, tool_name in enumerate(self._agent.last_tool_calls):
            emitter.emit_progress(
                event_type="optimize_tool_called",
                message=f"optimize tool called: {tool_name}",
                timeline_phase="tool_called",
                summary=f"optimize tool called: {tool_name}",
                data={
                    "tool_name": tool_name,
                    "tool_index": tool_index,
                },
            )
        emitter.emit_progress(
            event_type="optimize_tool_calls_completed",
            message="optimize tool calls completed",
            timeline_phase="tool_calls_completed",
            summary="optimize tool calls completed",
            data={
                "tool_call_count": len(self._agent.last_tool_calls),
                "tool_calls": list(self._agent.last_tool_calls),
            },
        )
        result = OptimizeResult(
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
        emitter.emit_progress(
            event_type="optimize_result_generated",
            message="optimize result generated",
            timeline_phase="result_generated",
            summary=output.summary,
            data={
                "patched_field_count": len(result.patched_fields),
                "skipped_field_count": len(result.skipped_fields),
                "patched_fields": [item.field_name for item in result.patched_fields],
                "patched_field_summaries": [
                    f"{item.field_name}: {item.reason}" if item.reason else item.field_name
                    for item in result.patched_fields
                ],
            },
        )
        emitter.emit_progress(
            event_type="optimize_result_ready",
            message="optimize result ready",
            timeline_phase="result_ready",
            summary=output.summary,
            data={
                "patched_field_count": len(result.patched_fields),
                "skipped_field_count": len(result.skipped_fields),
            },
        )
        emitter.emit_ended(
            event_type="optimize_completed",
            message="optimize runtime completed",
            summary=output.summary,
            data={
                "patched_field_count": len(result.patched_fields),
                "tool_call_count": len(self._agent.last_tool_calls),
            },
        )
        return result


def _run_optimize_agent(
    agent: OptimizeAgentLike,
    *,
    request: OptimizeRequest,
    deps: OptimizeToolDeps,
    context: OptimizeRuntimeContext | None,
) -> OptimizeAgentOutput:
    if context is None or context.managed_paths.llm_transcript_path is None:
        return agent.optimize(request, deps=deps)
    with llm_transcript_scope(context.managed_paths.llm_transcript_path):
        return agent.optimize(request, deps=deps)


def _write_runtime_artifacts(
    *,
    context: OptimizeRuntimeContext | None,
    prompt: str,
    tool_calls: list[str],
) -> None:
    if context is None:
        return
    context.managed_paths.prompt_path.write_text(prompt or "", encoding="utf-8")
    context.managed_paths.tool_calls_path.write_text(
        json.dumps({"tool_calls": tool_calls}, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _load_json(path_value: str | None) -> object:
    if not path_value:
        return None
    path = Path(path_value)
    if not path.exists():
        return None
    if path.is_dir():
        items: list[object] = []
        for child in sorted(path.iterdir()):
            if child.is_file() and child.suffix == ".json":
                items.append(json.loads(child.read_text(encoding="utf-8")))
        return items
    if not path.is_file():
        return None
    if path.suffix == ".jsonl":
        items = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                items.append(json.loads(line))
        return items
    return json.loads(path.read_text(encoding="utf-8"))


def _build_step_summaries(attempts: object) -> dict[int, dict[str, object]]:
    indexed: dict[int, dict[str, object]] = {}
    if not isinstance(attempts, list):
        return indexed
    for attempt in attempts:
        if not isinstance(attempt, dict):
            continue
        runner_history = attempt.get("runner_history")
        if not isinstance(runner_history, list):
            raw_artifacts = attempt.get("artifacts")
            artifacts = raw_artifacts if isinstance(raw_artifacts, dict) else {}
            runner_history = _load_json(_string_or_none(artifacts.get("runner_history")))
        if isinstance(runner_history, list):
            for item in runner_history:
                if not isinstance(item, dict):
                    continue
                step_index = item.get("step_index")
                if isinstance(step_index, int):
                    indexed.setdefault(step_index, dict(item))
            continue
        runner = attempt.get("runner")
        if isinstance(runner, dict):
            event_history = runner.get("event_history")
            if isinstance(event_history, list):
                for step_index, event in enumerate(event_history):
                    if isinstance(event, dict):
                        indexed.setdefault(step_index, dict(event))
    return indexed


def _string_or_none(value: object) -> str | None:
    return value if isinstance(value, str) else None


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
