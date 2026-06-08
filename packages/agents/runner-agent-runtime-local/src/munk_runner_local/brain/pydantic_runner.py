from __future__ import annotations

import json
import logging
from dataclasses import replace
from typing import Any, cast

from munk.agent_base.action import Action
from munk.agent_base.base import ActionHistoryEntry, Brain, ScreenState
from munk.agent_base.image_payload import encode_png_for_max_side
from munk.agent_base.llm import run_agent_sync_compatible
from munk.agent_base.output_strategy import append_system_prompt_suffix, build_structured_output_spec
from munk.agent_base.platform_profile import PlatformRunnerProfile, get_runner_profile
from munk.shared_tools import KnowledgeToolProvider
from pydantic_ai import Agent
from pydantic_ai.messages import BinaryImage, TextContent, UserContent

from munk.config.defaults import MUNK_CODE_DEFAULTS
from munk.config.schema import OutputStrategy
from munk.runtime_defaults import DEFAULT_VL_MAX_SIDE
from munk.services.events import RunEventSink
from munk.services.models import RunPaths
from munk_runner_local.action_feedback import (
    build_failed_runner_action_feedback,
    format_runner_action_feedback,
)
from munk_runner_local.brain.context_prep_models import ContextPrepKnowledgeItem, ContextPrepOutput
from munk_runner_local.brain.errors import RunnerProtocolError
from munk_runner_local.brain.history import build_action_history_entry, build_history_artifact
from munk_runner_local.brain.memory_store import RunnerMemoryStore
from munk_runner_local.brain.pydantic_runner_models import RunnerStepDeps
from munk_runner_local.brain.pydantic_runner_output_models import RunnerActionOutput, RunnerActionOutputModels
from munk_runner_local.brain.pydantic_runner_prompt import (
    build_runner_system_prompt,
    build_runner_user_prompt,
)
from munk_runner_local.brain.pydantic_runner_tools import (
    build_screen_summary_text,
    build_targets_seed_text,
    materialize_runner_action,
    record_contract_miss,
    record_seed_step_context,
    register_runner_tools,
)
from munk_runner_local.brain.runner_progress import (
    build_goal_progress_summary,
    build_prompt_history_summary,
)
from munk_runner_local.brain.runner_view import count_targets_in_text

SYSTEM_PROMPT = build_runner_system_prompt()
logger = logging.getLogger(__name__)


class PydanticAiRunnerBrain(Brain):
    def __init__(
        self,
        *,
        app_id: str = "unknown",
        knowledge_tools: KnowledgeToolProvider | None = None,
        case_brief: str,
        model: Any,
        output_strategy: OutputStrategy = "auto",
        paths: RunPaths,
        event_sink: RunEventSink | None = None,
        max_tokens: int = MUNK_CODE_DEFAULTS.runner.max_tokens,
        temperature: float = MUNK_CODE_DEFAULTS.runner.temperature,
        top_p: float = MUNK_CODE_DEFAULTS.runner.top_p,
        max_elements: int = MUNK_CODE_DEFAULTS.runner.max_elements,
        prompt_max_elements: int = MUNK_CODE_DEFAULTS.runner.prompt_max_elements,
        max_history: int = MUNK_CODE_DEFAULTS.runner.max_history,
        vl_max_side: int = DEFAULT_VL_MAX_SIDE,
        platform: str | None = None,
        profile: PlatformRunnerProfile | None = None,
        prepared_context_text: str = "none",
        prepared_knowledge_bundle: tuple[ContextPrepKnowledgeItem, ...] = (),
        prepared_selected_card_ids: tuple[str, ...] = (),
        context_prep_fallback_reason: str | None = None,
    ) -> None:
        self.app_id = app_id
        self.knowledge_tools = knowledge_tools
        self.case_brief = case_brief.strip()
        self.paths = paths
        self.event_sink = event_sink
        self.max_elements = max_elements
        self.prompt_max_elements = min(prompt_max_elements, max_elements)
        self.max_history = max_history
        self.vl_max_side = vl_max_side
        self.profile = profile or get_runner_profile(platform)
        self.prepared_context_text = prepared_context_text
        self.prepared_knowledge_bundle = prepared_knowledge_bundle
        self.prepared_selected_card_ids = prepared_selected_card_ids
        self.context_prep_fallback_reason = context_prep_fallback_reason
        self._current_step_index: int | None = None
        self._history: list[ActionHistoryEntry] = []
        self._memory_store = RunnerMemoryStore()
        output_spec = build_structured_output_spec(
            RunnerActionOutputModels,
            output_strategy=output_strategy,
        )
        self._agent = Agent[RunnerStepDeps, RunnerActionOutput](
            model=model,
            deps_type=RunnerStepDeps,
            output_type=output_spec.output_type,
            system_prompt=append_system_prompt_suffix(
                build_runner_system_prompt(self.profile),
                output_spec.system_prompt_suffix,
            ),
            name="pydantic_runner_brain",
            output_retries=1,
            model_settings={"temperature": temperature, "max_tokens": max_tokens, "top_p": top_p},
        )
        register_runner_tools(self._agent, platform=self.profile.platform)

    def on_step_started(self, step_index: int) -> None:
        self._current_step_index = step_index

    def apply_context_prep_output(
        self,
        output: ContextPrepOutput,
        *,
        knowledge_bundle: tuple[ContextPrepKnowledgeItem, ...] = (),
    ) -> None:
        self.prepared_context_text = output.prep_summary
        self.prepared_knowledge_bundle = knowledge_bundle
        self.prepared_selected_card_ids = tuple(item.card_id for item in output.selected_entries)
        self.context_prep_fallback_reason = output.fallback_reason

    def next_action(self, screen: ScreenState) -> Action:
        if not self.case_brief:
            return Action.stop(summary="empty case brief")

        self._attach_last_observation(screen)
        logger.info("pydantic_runner step=%s", self._current_step_index)
        deps = self._build_deps(screen)
        action = self._run_decision_attempt(screen, deps, retry_on_missing_action=True)
        self._record(action)
        return action

    def _build_deps(self, screen: ScreenState) -> RunnerStepDeps:
        return RunnerStepDeps(
            app_id=self.app_id,
            knowledge_tools=self.knowledge_tools,
            prepared_context_text=self.prepared_context_text,
            prepared_knowledge_bundle=self.prepared_knowledge_bundle,
            prepared_selected_card_ids=self.prepared_selected_card_ids,
            context_prep_fallback_reason=self.context_prep_fallback_reason,
            screen=screen,
            case_brief=self.case_brief,
            history_entries=self._history,
            max_elements=self.max_elements,
            run_dir=self.paths.run_dir,
            memory_store=self._memory_store,
            event_sink=self.event_sink,
            trace_path=self.paths.decision_trace_path,
            runner_memory_path=self.paths.runner_memory_path,
            step_index=self._current_step_index,
        )

    def _run_decision_attempt(
        self,
        screen: ScreenState,
        deps: RunnerStepDeps,
        *,
        retry_on_missing_action: bool,
        missing_action_attempted: bool = False,
    ) -> Action:
        deps.attempt_index += 1
        deps.attempt_tool_names.clear()
        targets_text = build_targets_seed_text(
            screen,
            max_elements=self.max_elements,
            prompt_max_elements=self.prompt_max_elements,
        )
        record_seed_step_context(
            deps,
            screen_summary=build_screen_summary_text(screen),
            targets_text=targets_text,
            seeded_element_count=self._count_seeded_elements(targets_text),
        )
        user_prompt = self._build_user_prompt(screen, missing_action_attempted=missing_action_attempted)
        output_excerpt = "none"
        try:
            result = run_agent_sync_compatible(self._agent, user_prompt=user_prompt, deps=deps)
            logger.info("pydantic_runner output=%s", result.output)
            output_excerpt = self._build_output_excerpt(result.output)
            return materialize_runner_action(deps, result.output)
        except ValueError as exc:
            output_excerpt = str(exc).strip() or "invalid structured action"
            logger.warning("pydantic_runner structured_output_error=%s", output_excerpt)
            feedback = self._build_failed_feedback(result.output, exc) if "result" in locals() else None
            if feedback is not None:
                screen = replace(screen, last_action_feedback=feedback)
        except Exception:
            raise

        if retry_on_missing_action:
            record_contract_miss(
                deps,
                output_excerpt=output_excerpt,
                will_retry=True,
                seeded_element_count=self._seeded_element_count(screen),
            )
            logger.warning(
                "pydantic_runner contract_miss: finished without valid structured action; retrying once"
            )
            return self._run_decision_attempt(
                screen,
                deps,
                retry_on_missing_action=False,
                missing_action_attempted=True,
            )
        record_contract_miss(
            deps,
            output_excerpt=output_excerpt,
            will_retry=False,
            seeded_element_count=self._seeded_element_count(screen),
        )
        message = (
            "runner agent finished without valid structured action after retry; "
            "must return exactly one structured action output"
        )
        logger.error("pydantic_runner protocol_error=%s", message)
        raise RunnerProtocolError(
            message,
            step_index=deps.step_index,
            attempt_count=deps.attempt_index,
            last_output_excerpt=output_excerpt,
            tool_names_seen=deps.attempt_tool_names,
        )

    @staticmethod
    def _build_failed_feedback(output: object, exc: ValueError):
        if not hasattr(output, "model_dump") or not hasattr(output, "action_type"):
            return None
        action_type = getattr(output, "action_type", None)
        if not isinstance(action_type, str):
            return None
        payload = cast(Any, output).model_dump(exclude_none=True)
        return build_failed_runner_action_feedback(
            action_type=action_type,
            arguments=payload,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )

    def _build_user_prompt(
        self,
        screen: ScreenState,
        *,
        missing_action_attempted: bool = False,
    ) -> list[UserContent]:
        prompt_text = build_runner_user_prompt(
            case_brief=self.case_brief,
            history_summary=self._format_history(),
            last_outcome=self._last_action_outcome(screen),
            last_action_feedback=self._last_action_feedback(screen),
            goal_progress=self._goal_progress(screen),
            prepared_context_text=self.prepared_context_text,
            prepared_knowledge_text=self._format_prepared_knowledge_text(),
            context_prep_fallback_reason=self.context_prep_fallback_reason,
            screen_summary=build_screen_summary_text(screen),
            targets_text=build_targets_seed_text(
                screen,
                max_elements=self.max_elements,
                prompt_max_elements=self.prompt_max_elements,
            ),
            missing_action_attempted=missing_action_attempted,
        )
        content: list[UserContent] = [
            TextContent(content=prompt_text)
        ]
        image = self._screen_image(screen)
        if image is not None:
            content.append(image)
        return content

    def _format_prepared_knowledge_text(self) -> str:
        if not self.prepared_knowledge_bundle:
            return "none"
        blocks: list[str] = []
        for item in self.prepared_knowledge_bundle:
            lines = [f"- card_id: {item.card_id}"]
            lines.append(f"  title: {item.title}")
            lines.append(f"  card_type: {item.card_type}")
            lines.extend(f"  {line}" for line in item.summary_text.splitlines())
            blocks.append("\n".join(lines))
        return "\n".join(blocks)

    def _screen_image(self, screen: ScreenState) -> BinaryImage | None:
        if screen.image_bgr is None:
            return None
        png_bytes = encode_png_for_max_side(screen.image_bgr, self.vl_max_side)
        if not png_bytes:
            return None
        return BinaryImage(png_bytes, media_type="image/png", identifier="current_screen")

    def _attach_last_observation(self, screen: ScreenState) -> None:
        if not self._history:
            return
        observation = screen.last_action_observation
        if observation is None:
            return
        latest = self._history[-1]
        if latest.outcome_summary == observation.summary:
            return
        self._history[-1] = replace(latest, outcome_summary=observation.summary)
        self._write_history_artifact()
        self._write_memory_artifact()

    def _format_history(self) -> str:
        return build_prompt_history_summary(self._history[-self.max_history :])

    def _goal_progress(self, screen: ScreenState) -> str:
        return build_goal_progress_summary(self._history[-self.max_history :], screen)

    @staticmethod
    def _last_action_feedback(screen: ScreenState) -> str:
        return format_runner_action_feedback(screen.last_action_feedback)

    @staticmethod
    def _last_action_outcome(screen: ScreenState) -> str:
        observation = screen.last_action_observation
        if observation is None or not observation.summary:
            return "none"
        return observation.summary

    def _record(self, action: Action) -> None:
        self._history.append(build_action_history_entry(action))
        self._write_history_artifact()

    def _write_history_artifact(self) -> None:
        history_path = self.paths.runner_history_path
        if history_path is None:
            return
        payload = build_history_artifact(self._history, max_entries=max(self.max_history, 10))
        history_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def _write_memory_artifact(self) -> None:
        memory_path = self.paths.runner_memory_path
        if memory_path is None:
            return
        memory_path.write_text(self._memory_store.artifact_json(), encoding="utf-8")

    @staticmethod
    def _build_output_excerpt(output: object) -> str:
        text = str(output).strip()
        if not text:
            return "empty output"
        compact = " ".join(text.split())
        if len(compact) > 160:
            return compact[:157] + "..."
        return compact

    def _seeded_element_count(self, screen: ScreenState) -> int:
        targets_text = build_targets_seed_text(
            screen,
            max_elements=self.max_elements,
            prompt_max_elements=self.prompt_max_elements,
        )
        return count_targets_in_text(targets_text)

    @staticmethod
    def _count_seeded_elements(targets_text: str) -> int:
        if targets_text == "none":
            return 0
        return count_targets_in_text(targets_text)
