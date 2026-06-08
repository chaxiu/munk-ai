from __future__ import annotations

import json
from typing import Any, cast

from munk.agent_base.llm import run_agent_sync_compatible
from munk.agent_base.output_strategy import append_system_prompt_suffix, build_structured_output_spec
from pydantic_ai import Agent
from pydantic_ai.messages import TextContent, UserContent

from munk.config.defaults import MUNK_CODE_DEFAULTS
from munk.config.schema import OutputStrategy
from munk.runtime_defaults import DEFAULT_VL_MAX_SIDE

from .agent_models import JudgeAgentOutput
from .image_payloads import load_screenshot_binary_image
from .models import JudgeEvidencePack
from .step_projection import build_recent_step_summaries
from .tool_models import JudgeRunDeps
from .tools import register_judge_tools

SYSTEM_PROMPT = "\n".join(
    [
        "You are a judge agent for mobile UI automation test cases.",
        "Decide whether the provided evidence proves the case passed, failed, or is inconclusive.",
        "Use only the provided evidence. Never invent unseen UI states or hidden business logic.",
        "Prefer inconclusive over pass when the evidence is incomplete or ambiguous.",
        "Treat explicit execution failures as failure if they are present in the evidence pack.",
        "A completed runner stop does not automatically mean the case passed.",
        "An incomplete run does not automatically mean inconclusive.",
        "If the evidence shows the runner explored relevant screens repeatedly but never found a required entry, action, or affordance, you may return failed with a concrete reason.",
        "Use PRIMARY_EVIDENCE first. Read tools are fallback only when those primary excerpts are still insufficient.",
        "Write summary as a short verdict statement.",
        "Write reason as an expected-versus-observed business difference, not as generic judge commentary.",
        "For failed or inconclusive verdicts, failure_hypothesis must be one concise product-facing hypothesis such as 'save succeeded but list did not update', 'entry exists but is not reachable', or 'state toggle did not persist'.",
        "For passed verdicts, omit failure_hypothesis unless a useful residual risk must be noted.",
        "When the evidence suggests the case wording or execution guidance should be improved for future runs, set needs_optimization=true and choose the smallest relevant ai_guidance fields to update.",
        "Only request optimization for durable case-quality issues such as ambiguity, missing preflight expectations, interaction confusion, weak recovery guidance, or judge misread risk.",
        "Explain the verdict briefly and cite the most relevant evidence ids.",
        "Return only the structured output.",
    ]
)


class PydanticAiJudgeAgent:
    def __init__(
        self,
        *,
        model: Any,
        output_strategy: OutputStrategy = "auto",
        max_tokens: int = MUNK_CODE_DEFAULTS.judge.max_tokens,
        temperature: float = MUNK_CODE_DEFAULTS.judge.temperature,
        vl_max_side: int = DEFAULT_VL_MAX_SIDE,
    ) -> None:
        self._vl_max_side = vl_max_side
        self.last_prompt = ""
        self.last_tool_calls: list[str] = []
        output_spec = build_structured_output_spec(JudgeAgentOutput, output_strategy=output_strategy)
        self._agent = Agent(
            model=cast(Any, model),
            deps_type=JudgeRunDeps,
            output_type=output_spec.output_type,
            system_prompt=append_system_prompt_suffix(SYSTEM_PROMPT, output_spec.system_prompt_suffix),
            name="pydantic_case_judge_agent",
            model_settings={
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        register_judge_tools(self._agent)

    def judge(self, evidence_pack: JudgeEvidencePack) -> JudgeAgentOutput:
        vl_max_side = getattr(self, "_vl_max_side", DEFAULT_VL_MAX_SIDE)
        deps = JudgeRunDeps(evidence_pack=evidence_pack, vl_max_side=vl_max_side)
        user_prompt = self._build_user_prompt(evidence_pack)
        self.last_prompt = self._build_prompt(evidence_pack)
        result = run_agent_sync_compatible(
            self._agent,
            user_prompt=user_prompt,
            deps=deps,
        )
        self.last_tool_calls = list(deps.tool_calls)
        return result.output

    @staticmethod
    def _build_prompt(evidence_pack: JudgeEvidencePack) -> str:
        expected_lines = evidence_pack.expected or ["none"]
        preconditions = evidence_pack.preconditions or ["none"]
        primary_lines = [
            PydanticAiJudgeAgent._format_primary_evidence(item)
            for item in evidence_pack.primary_evidence[:4]
        ] or ["- none"]
        recent_step_summary_lines = [
            PydanticAiJudgeAgent._format_recent_step_summary(item)
            for item in build_recent_step_summaries(JudgeRunDeps(evidence_pack=evidence_pack), 5)
        ] or ["- none"]
        guidance_lines = PydanticAiJudgeAgent._format_ai_guidance(evidence_pack)
        runner_memory_lines = [
            PydanticAiJudgeAgent._format_runner_memory_summary(item)
            for item in evidence_pack.runner_memory_summary
        ] or ["- none"]
        final_screenshot = PydanticAiJudgeAgent._select_final_raw_screenshot(evidence_pack)
        final_screenshot_lines = (
            [PydanticAiJudgeAgent._format_final_screenshot_line(final_screenshot)]
            if final_screenshot is not None
            else ["- none"]
        )
        supporting_lines = [
            f"- {item.evidence_id} [{item.kind}/{item.source}] {item.summary}"
            for item in evidence_pack.supporting_evidence[:8]
        ] or ["- none"]
        error_log_lines = [
            PydanticAiJudgeAgent._format_runtime_error_log(item)
            for item in evidence_pack.evidence
            if item.kind == "runtime_error_log"
        ] or ["- none"]
        return "\n".join(
            [
                "[RULES]",
                "- Use only the provided evidence.",
                "- Do not assume completed means passed.",
                "- Prefer PRIMARY_EVIDENCE over SUPPORTING_EVIDENCE.",
                "- Treat recent compact tree, screenshots, and screen diffs as the strongest state evidence.",
                "- Use runner history as action context, not as a replacement for visual or structural proof.",
                "- Read screenshots in step order and reason about state transitions before the final verdict.",
                "- `reason` must describe the business gap in the form of expected versus observed behavior.",
                "- Good `reason` example: expected the saved task to appear in the list, observed the app returned to the list but the new task was missing.",
                "- Bad `reason` example: evidence was insufficient or the case failed.",
                "- For failed or inconclusive verdicts, `failure_hypothesis` must be exactly one concise product-facing sentence.",
                "- Good `failure_hypothesis` examples: save succeeded but list did not update; entry exists but is not reachable; state toggle did not persist.",
                "- Bad `failure_hypothesis` examples: test failed; evidence unclear; runner had issues.",
                "",
                "[OBJECTIVE]",
                f"Plan ID: {evidence_pack.plan_id}",
                f"Case ID: {evidence_pack.case_id}",
                f"Case Title: {evidence_pack.case_title}",
                f"Intent: {evidence_pack.intent}",
                "Preconditions:",
                *[f"- {item}" for item in preconditions],
                "Expected:",
                *[f"- {item}" for item in expected_lines],
                "Runner Goal:",
                *PydanticAiJudgeAgent._format_runner_goal(evidence_pack.runner_goal),
                "",
                "[AI_GUIDANCE]",
                *guidance_lines,
                "",
                "[EXECUTION]",
                f"- status={evidence_pack.execution.status}",
                f"- stop_reason={evidence_pack.execution.stop_reason or 'none'}",
                f"- steps_completed={evidence_pack.execution.steps_completed}",
                f"- error_type={evidence_pack.execution.error_type or 'none'}",
                f"- error_message={evidence_pack.execution.error_message or 'none'}",
                f"- last_action_summary={evidence_pack.execution.last_action_summary or 'none'}",
                f"- last_target_identity={evidence_pack.execution.last_target_identity or 'none'}",
                f"- last_surface_identity={evidence_pack.execution.last_surface_identity or 'none'}",
                "",
                "[PRIMARY_EVIDENCE]",
                *primary_lines,
                "",
                "[RECENT_STEP_SUMMARIES]",
                *recent_step_summary_lines,
                "",
                "[RUNNER_MEMORY_SUMMARY]",
                *runner_memory_lines,
                "",
                "[FINAL_SCREENSHOT]",
                *final_screenshot_lines,
                "",
                "[ERROR_LOG_EVIDENCE]",
                *error_log_lines,
                "",
                "[SUPPORTING_EVIDENCE]",
                *supporting_lines,
                "",
                "[TOOL_POLICY]",
                "- Read tools are fallback only.",
                "- When PRIMARY_EVIDENCE is insufficient, call `read_recent_step_summaries` first for a global view.",
                "- If one step becomes important, call `read_step_summary` before requesting detailed step evidence.",
                "- Use `read_step_screen` or `read_step_transition` only when step summaries still leave a business gap unresolved.",
                "- Use `read_runner_memory` when runner-saved baseline facts may decide the verdict.",
                "- Use `read_step_screen_raw_image` when a raw screenshot is needed for visual confirmation.",
                "- Use at most a small number of tool calls when PRIMARY_EVIDENCE is insufficient.",
            ]
        )

    @staticmethod
    def _format_ai_guidance(evidence_pack: JudgeEvidencePack) -> list[str]:
        guidance = evidence_pack.ai_guidance
        if guidance is None:
            return ["- none"]
        sections = [
            ("Objective Clarifications", guidance.objective_clarifications),
            ("Judge Hints", guidance.judge_hints),
        ]
        lines: list[str] = []
        for title, items in sections:
            cleaned = [item.strip() for item in items if item.strip()]
            if not cleaned:
                continue
            lines.append(f"{title}:")
            lines.extend(f"- {item}" for item in cleaned)
        return lines or ["- none"]

    def _build_user_prompt(self, evidence_pack: JudgeEvidencePack) -> list[UserContent]:
        content: list[UserContent] = [TextContent(content=PydanticAiJudgeAgent._build_prompt(evidence_pack))]
        screenshot = self._select_final_raw_screenshot(evidence_pack)
        vl_max_side = getattr(self, "_vl_max_side", DEFAULT_VL_MAX_SIDE)
        if screenshot is not None:
            content.append(
                TextContent(
                    content=PydanticAiJudgeAgent._format_final_screenshot_prompt(screenshot.model_dump(mode="json"))
                )
            )
            image = load_screenshot_binary_image(
                screenshot.path,
                identifier=f"judge_step_{screenshot.step_index:04d}_{screenshot.kind}",
                vl_max_side=vl_max_side,
            )
            if image is not None:
                content.append(image)
        return content

    @staticmethod
    def _format_primary_evidence(item: Any) -> str:
        excerpt: object = item.payload.get("excerpt")
        excerpt_text = "none"
        if excerpt is not None:
            excerpt_text = json.dumps(excerpt, ensure_ascii=False, sort_keys=True)
        return (
            f"- {item.evidence_id} [{item.kind}/{item.source}] {item.summary}\n"
            f"  excerpt={excerpt_text}"
        )

    @staticmethod
    def _format_recent_step_summary(item: dict[str, object]) -> str:
        return (
            f"- step={item.get('step_index')} "
            f"action={item.get('action_summary') or 'none'} "
            f"outcome={item.get('outcome_summary') or 'none'} "
            f"screen_change={item.get('screen_change_status') or 'unknown'} "
            f"has_screen={item.get('has_screen')} "
            f"has_transition={item.get('has_transition')}"
        )

    @staticmethod
    def _format_runner_memory_summary(item: dict[str, object]) -> str:
        return (
            f"- key={item.get('key') or 'unknown'} "
            f"summary={item.get('summary') or 'none'} "
            f"updated_step={item.get('updated_step_index')}"
        )

    @staticmethod
    def _format_final_screenshot_line(item: Any) -> str:
        return (
            f"- step={item.step_index} kind={item.kind} "
            f"action={item.action_summary or 'none'} "
            f"observation={item.observation_summary or 'none'}"
        )

    @staticmethod
    def _format_final_screenshot_prompt(item: dict[str, object]) -> str:
        return "\n".join(
            [
                "[FINAL_SCREENSHOT]",
                f"Step: {item.get('step_index')}",
                f"Kind: {item.get('kind')}",
                f"Action Summary: {item.get('action_summary') or 'none'}",
                f"Observation Summary: {item.get('observation_summary') or 'none'}",
                "This is the final raw screenshot seed for the current judge turn.",
            ]
        )

    @staticmethod
    def _format_runtime_error_log(item: Any) -> str:
        excerpt: object = item.payload.get("excerpt")
        excerpt_text = str(excerpt).strip() if excerpt is not None else "none"
        return f"- {item.evidence_id} [{item.kind}/{item.source}] {item.summary}\n{excerpt_text}"

    @staticmethod
    def _format_runner_goal(goal: str) -> list[str]:
        lines = [line.rstrip() for line in goal.splitlines() if line.strip()]
        return lines or ["none"]

    @staticmethod
    def _select_final_raw_screenshot(evidence_pack: JudgeEvidencePack) -> Any | None:
        if not evidence_pack.recent_raw_screenshots:
            return None
        return max(evidence_pack.recent_raw_screenshots, key=lambda item: item.step_index)
