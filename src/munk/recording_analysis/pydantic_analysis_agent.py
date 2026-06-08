from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import cv2
from pydantic_ai import Agent
from pydantic_ai.messages import BinaryImage, TextContent, UserContent

from munk.agent_base.image_payload import encode_png_for_max_side
from munk.agent_base.output_strategy import append_system_prompt_suffix, build_structured_output_spec
from munk.config.schema import OutputStrategy
from munk.perception.image import BgrImage
from munk.recording import RecordingAnalysisStep
from munk.runtime_defaults import DEFAULT_VL_MAX_SIDE

from .models import (
    AppendProcedureStepSubmission,
    FinalizeAttemptOutcome,
    FinalizeCaseSubmission,
    FinalizeStageDeps,
    FinalizeStepSummary,
    StepAttemptOutcome,
    StepStageDeps,
)
from .pydantic_analysis_tools import register_finalize_read_tools, register_step_read_tools

_STEP_SYSTEM_PROMPT = "\n".join(
    [
        "You are a recording analysis agent for mobile UI test cases.",
        "Analyze one ordered interaction step at a time.",
        "Read the before screenshot first, then the after screenshot.",
        "Use page identity, action evidence, outcome evidence, and screenshots to infer the user's intent and the visible state change.",
        "Return exactly one structured step analysis with action, intent, state_change, and warnings.",
        "Use read_* tools sparingly. If a tool returns a budget-exhausted message, stop reading and return the structured step analysis immediately.",
        "First determine the most likely user intent from the before and after screens.",
        "Then describe the direct action in action and the visible result in state_change.",
        "Do not reduce back, close, blank-area taps, or swipes to raw action names if the intent is visible from the screen transition.",
        "Read the raw tree only if the structured evidence is insufficient.",
        "Do not copy pointer, ack, or raw forwarding payload into action, intent, or state_change.",
        "Do not invent page_id, page navigation metadata, or hidden business logic.",
        "Do not invent hidden business logic beyond the visible evidence.",
        "Prefer concise, user-observable wording.",
        "Return only the structured output.",
    ]
)

_FINALIZE_SYSTEM_PROMPT = "\n".join(
    [
        "You are a recording analysis agent for mobile UI test cases.",
        "Given stable structured step summaries extracted from a recording, produce a canonical test case draft.",
        "Return one structured case draft.",
        "Use read_* tools sparingly. If a tool returns a budget-exhausted message, stop reading and return the structured case draft immediately.",
        "Keep title and intent concise and human-readable.",
        "expected must contain only natural-language, user-observable weak assertions.",
        "runner_goal must describe a single runnable execution objective.",
        "Use step intents to infer the case-level goal.",
        "Use step state changes to strengthen expected outcomes.",
        "Use the provided procedure_step values as the final step wording style.",
        "Do not repeat low-level pointer details.",
        "Do not generate page_id or any page navigation metadata.",
        "Return only the structured output.",
    ]
)


class PydanticAiRecordingAnalysisAgent:
    def __init__(
        self,
        *,
        model: object,
        output_strategy: OutputStrategy = "auto",
        max_tokens: int = 2048,
        temperature: float = 0.0,
        vl_max_side: int = DEFAULT_VL_MAX_SIDE,
    ) -> None:
        self._vl_max_side = vl_max_side
        settings = cast(Any, {"temperature": temperature, "max_tokens": max_tokens})
        step_output_spec = build_structured_output_spec(
            AppendProcedureStepSubmission,
            output_strategy=output_strategy,
        )
        finalize_output_spec = build_structured_output_spec(
            FinalizeCaseSubmission,
            output_strategy=output_strategy,
        )
        self._step_agent = Agent(
            model=cast(Any, model),
            deps_type=StepStageDeps,
            output_type=step_output_spec.output_type,
            system_prompt=append_system_prompt_suffix(
                _STEP_SYSTEM_PROMPT,
                step_output_spec.system_prompt_suffix,
            ),
            name="pydantic_recording_step_analysis_agent",
            model_settings=settings,
        )
        self._finalize_agent = Agent(
            model=cast(Any, model),
            deps_type=FinalizeStageDeps,
            output_type=finalize_output_spec.output_type,
            system_prompt=append_system_prompt_suffix(
                _FINALIZE_SYSTEM_PROMPT,
                finalize_output_spec.system_prompt_suffix,
            ),
            name="pydantic_recording_case_finalize_agent",
            model_settings=settings,
        )
        register_step_read_tools(self._step_agent)
        register_finalize_read_tools(self._finalize_agent)

    def run_step_attempt(
        self,
        *,
        bundle: dict[str, Any],
        step: dict[str, Any],
        history_procedure: list[str],
        attempt_index: int,
        retry_feedback: str | None = None,
    ) -> StepAttemptOutcome:
        deps = StepStageDeps(
            bundle=bundle,
            step=step,
            history_procedure=history_procedure,
            attempt_index=attempt_index,
            retry_feedback=retry_feedback,
        )
        try:
            result = self._step_agent.run_sync(
                user_prompt=self._build_step_prompt(
                    step=step,
                    history_procedure=history_procedure,
                    attempt_index=attempt_index,
                    retry_feedback=retry_feedback,
                ),
                deps=deps,
            )
        except Exception as exc:
            return StepAttemptOutcome(
                submission=None,
                output_excerpt=str(exc),
                last_error=deps.last_submission_error or str(exc),
                tool_names_seen=list(deps.attempt_tool_names),
            )
        return StepAttemptOutcome(
            submission=result.output,
            output_excerpt=_build_output_excerpt(result.output),
            last_error=deps.last_submission_error,
            tool_names_seen=list(deps.attempt_tool_names),
        )

    def run_finalize_attempt(
        self,
        *,
        bundle: dict[str, Any],
        analyzed_steps: list[RecordingAnalysisStep],
        warnings: list[str],
        attempt_index: int,
        retry_feedback: str | None = None,
    ) -> FinalizeAttemptOutcome:
        step_summaries = [
            FinalizeStepSummary(
                action=item.action or item.summary or str(item.kind),
                intent=item.intent or item.procedure_step or item.summary or str(item.kind),
                state_change=item.state_change or item.procedure_step or item.summary or str(item.kind),
                procedure_step=item.procedure_step or item.summary or str(item.kind),
            )
            for item in analyzed_steps
        ]
        deps = FinalizeStageDeps(
            bundle=bundle,
            step_summaries=step_summaries,
            warnings=warnings,
            attempt_index=attempt_index,
            retry_feedback=retry_feedback,
        )
        try:
            result = self._finalize_agent.run_sync(
                user_prompt=self._build_finalize_prompt(
                    bundle=bundle,
                    analyzed_steps=analyzed_steps,
                    attempt_index=attempt_index,
                    retry_feedback=retry_feedback,
                ),
                deps=deps,
            )
        except Exception as exc:
            return FinalizeAttemptOutcome(
                submission=None,
                output_excerpt=str(exc),
                last_error=deps.last_submission_error or str(exc),
                tool_names_seen=list(deps.attempt_tool_names),
            )
        return FinalizeAttemptOutcome(
            submission=result.output,
            output_excerpt=_build_output_excerpt(result.output),
            last_error=deps.last_submission_error,
            tool_names_seen=list(deps.attempt_tool_names),
        )

    def _build_step_prompt(
        self,
        *,
        step: dict[str, Any],
        history_procedure: list[str],
        attempt_index: int,
        retry_feedback: str | None = None,
    ) -> list[UserContent]:
        entry = cast(dict[str, Any], step["entry"])
        before_screenshot = cast(dict[str, Any], step["before_screenshot"])
        after_screenshot = cast(dict[str, Any], step["after_screenshot"])
        before_observation = cast(dict[str, Any], step["before_observation"]["observation"])
        after_observation = cast(dict[str, Any], step["after_observation"]["observation"])
        page_identity = cast(dict[str, Any], step.get("page_identity") or {})
        action_evidence = cast(dict[str, Any], step.get("action_evidence") or {})
        outcome_evidence = cast(dict[str, Any], step.get("outcome_evidence") or {})
        history_lines = [f"- {item}" for item in history_procedure] or ["- none"]
        prompt_lines = [
            "[SESSION]",
            f"Recording ID: {step['entry']['recording_id']}",
            f"Attempt: {attempt_index}",
            "",
            "[HISTORY_PROCEDURE]",
            *history_lines,
            "",
            "[STEP_META]",
            f"Seq: {entry.get('seq')}",
            f"Kind: {entry.get('kind')}",
            f"Summary: {entry.get('summary') or 'none'}",
            f"Before Observation: {before_observation.get('observation_id')}",
            f"After Observation: {after_observation.get('observation_id')}",
            f"Before Screen: {before_screenshot.get('summary') or 'none'}",
            f"After Screen: {after_screenshot.get('summary') or 'none'}",
            "Analyze this single state transition only.",
            "Return one structured step analysis with action, intent, state_change, and warnings.",
            "",
            "[PAGE_IDENTITY]",
            f"before_entry_identity={page_identity.get('before_entry_identity') or 'none'}",
            f"after_entry_identity={page_identity.get('after_entry_identity') or 'none'}",
            f"before_surface_identity={page_identity.get('before_surface_identity') or 'none'}",
            f"after_surface_identity={page_identity.get('after_surface_identity') or 'none'}",
            "",
            "[ACTION_EVIDENCE]",
            f"action_kind={action_evidence.get('action_kind') or entry.get('kind') or 'unknown'}",
            f"raw_action={action_evidence.get('raw_action_summary') or 'none'}",
            f"resolved_target={self._summarize_target(action_evidence.get('resolved_target'))}",
            f"target_candidates={self._summarize_candidates(action_evidence.get('target_candidates'))}",
            f"action_warnings={self._summarize_warnings(action_evidence.get('warnings'))}",
            "",
            "[OUTCOME_EVIDENCE]",
            f"screen_diff_summary={outcome_evidence.get('screen_diff_summary') or self._tree_diff_summary(step)}",
            f"outcome_warnings={self._summarize_warnings(outcome_evidence.get('warnings'))}",
            "Analyze this single state transition only.",
            "Infer the most likely user intent before writing action or state_change.",
            "Return one structured step analysis with action, intent, state_change, and warnings.",
        ]
        if retry_feedback:
            prompt_lines.extend(["", "[RETRY_FEEDBACK]", retry_feedback])
        contents: list[UserContent] = [TextContent(content="\n".join(prompt_lines))]
        self._append_step_image(contents, screenshot=before_screenshot, step_seq=entry["seq"], role="before")
        self._append_step_image(contents, screenshot=after_screenshot, step_seq=entry["seq"], role="after")
        return contents

    def _build_finalize_prompt(
        self,
        *,
        bundle: dict[str, Any],
        analyzed_steps: list[RecordingAnalysisStep],
        attempt_index: int,
        retry_feedback: str | None = None,
    ) -> str:
        session = cast(dict[str, Any], bundle["session"])
        step_lines = [
            (
                f"- step={item.seq}; action={item.action or 'none'}; intent={item.intent or 'none'}; "
                f"state_change={item.state_change or 'none'}; procedure_step={item.procedure_step or item.summary or item.kind}"
            )
            for item in analyzed_steps
        ] or ["- none"]
        lines = [
            "[SESSION]",
            f"Recording ID: {session.get('recording_id')}",
            f"App ID: {session.get('app_id')}",
            f"Case ID: {session.get('case_id') or 'none'}",
            f"Source Summary: {bundle.get('source_summary') or 'none'}",
            f"Attempt: {attempt_index}",
            "",
            "[STEP_SUMMARIES]",
            *step_lines,
            "",
            "[EXPECTATIONS]",
            "- expected should stay natural-language and user-observable.",
            "- do not include page_id or page navigation metadata.",
            "- use step intents to infer the case-level purpose.",
            "- use step state changes to infer visible expectations.",
            "- return one structured case draft.",
        ]
        if retry_feedback:
            lines.extend(["", "[RETRY_FEEDBACK]", retry_feedback])
        return "\n".join(lines)

    def _append_step_image(
        self,
        contents: list[UserContent],
        *,
        screenshot: dict[str, Any],
        step_seq: int,
        role: str,
    ) -> None:
        contents.append(
            TextContent(
                content="\n".join(
                    [
                        "[STEP_IMAGE]",
                        f"Seq: {step_seq}",
                        f"Role: {role}",
                        f"Observation ID: {screenshot.get('observation_id')}",
                        f"Entry Identity: {screenshot.get('entry_identity') or 'none'}",
                        f"Surface Identity: {screenshot.get('surface_identity') or 'none'}",
                        f"Summary: {screenshot.get('summary') or 'none'}",
                        "Read these screenshots in order: before first, then after.",
                    ]
                )
            )
        )
        image = self._load_png_binary(
            cast(str, screenshot["path"]),
            identifier=f"recording_step_{step_seq:04d}_{role}",
        )
        if image is not None:
            contents.append(image)

    @staticmethod
    def _tree_diff_summary(step: dict[str, Any]) -> str:
        tree_diff = step.get("tree_diff")
        if not isinstance(tree_diff, dict):
            return "none"
        summary = cast(object | None, tree_diff.get("summary"))
        return str(summary) if summary else "none"

    @staticmethod
    def _summarize_target(target: object) -> str:
        if not isinstance(target, dict):
            return "none"
        payload = cast(dict[str, object], target)
        label = str(payload.get("label") or "none")
        kind = str(payload.get("kind") or "none")
        source = str(payload.get("source") or "none")
        confidence = cast(object | None, payload.get("confidence"))
        bounds = cast(object | None, payload.get("bounds")) if payload.get("bounds") is not None else "none"
        return (
            f"label={label}; kind={kind}; source={source}; "
            f"confidence={confidence if confidence is not None else 'none'}; bounds={bounds}"
        )

    @staticmethod
    def _summarize_candidates(value: object) -> str:
        if not isinstance(value, list) or not value:
            return "none"
        parts: list[str] = []
        for raw in cast(list[object], value[:3]):
            if not isinstance(raw, dict):
                continue
            payload = cast(dict[str, object], raw)
            parts.append(
                f"rank={payload.get('rank') or '?'} "
                f"label={str(payload.get('label') or 'none')} "
                f"kind={str(payload.get('kind') or 'none')} "
                f"confidence={payload.get('confidence') if payload.get('confidence') is not None else 'none'}"
            )
        return " | ".join(parts) if parts else "none"

    @staticmethod
    def _summarize_warnings(value: object) -> str:
        if not isinstance(value, list) or not value:
            return "none"
        return " | ".join(str(item) for item in cast(list[object], value[:3]))

    def _load_png_binary(self, path_value: str, *, identifier: str) -> BinaryImage | None:
        path = Path(path_value)
        if not path.exists():
            return None
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None:
            return BinaryImage(path.read_bytes(), media_type="image/png", identifier=identifier)
        png_bytes = encode_png_for_max_side(cast(BgrImage, image), getattr(self, "_vl_max_side", DEFAULT_VL_MAX_SIDE))
        if not png_bytes:
            return None
        return BinaryImage(png_bytes, media_type="image/png", identifier=identifier)


def _build_output_excerpt(output: AppendProcedureStepSubmission | FinalizeCaseSubmission) -> str:
    cleaned = output.model_dump_json(exclude_none=True)
    if not cleaned:
        return "none"
    return cleaned[:400]
