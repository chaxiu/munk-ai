from __future__ import annotations

from typing import Any, cast

from munk.agent_base.llm import run_agent_sync_compatible
from munk.agent_base.output_strategy import append_system_prompt_suffix, build_structured_output_spec
from munk.reviewing.orchestration_models import ReviewOrchestrationContract
from munk.shared_tools import KnowledgeToolProvider
from munk.testing import TestCase
from pydantic_ai import Agent

from munk.config.defaults import MUNK_CODE_DEFAULTS
from munk.config.schema import OutputStrategy
from munk.planning.models import ChangePlanInput, RequirementInput

from .draft_models import GeneratedCaseAppendDraft, GeneratedPlanFinalizeDraft, GeneratedPlanSkeletonDraft
from .shared_tools import PlanAppKnowledgeDeps, register_plan_app_knowledge_tools

SKELETON_SYSTEM_PROMPT = "\n".join(
    [
        "You are a planning agent for app UI testing.",
        "Generate only a compact plan skeleton, not full test cases.",
        "Return a concise name, a concise summary, and a target_case_count.",
        "name must be short, human-readable, and suitable for direct UI display.",
        "Do not use generated ids, timestamps, or generic placeholders like plan-1.",
        "target_case_count must be a positive integer and must stay within the requested max cases.",
        "Prefer small, distinct, high-value plans with minimal overlap.",
    ]
)

APPEND_SYSTEM_PROMPT = "\n".join(
    [
        "You are a planning agent for app UI testing.",
        "Generate exactly one structured test case at a time.",
        "Each case must include title, intent, runner_goal, and start_mode.",
        "runner_goal must describe one single-case execution objective for the current runner.",
        "preconditions must list only required setup constraints; leave them empty when none exist.",
        "expected must contain at least one user-observable, verifiable outcome; do not use filler text.",
        "procedure is optional and should be omitted unless there is clear value in preserving a short step outline.",
        "Always set start_mode='reset'.",
        "Return page_id as null. Do not infer, generate, or guess any page identifier.",
        "Do not generate judge/report fields.",
        "Do not decide is_core_case; humans maintain that separately.",
        "Avoid duplicating already-generated cases.",
    ]
)

FINALIZE_SYSTEM_PROMPT = "\n".join(
    [
        "You are a planning agent for app UI testing.",
        "Finalize a plan after all cases have already been generated.",
        "Return only a concise final summary.",
        "Do not add, remove, or rewrite cases in this step.",
    ]
)


class PydanticAiPlanAgent:
    def __init__(
        self,
        *,
        model: Any,
        output_strategy: OutputStrategy = "auto",
        max_cases: int = MUNK_CODE_DEFAULTS.plan.max_cases,
        max_tokens: int = MUNK_CODE_DEFAULTS.plan.max_tokens,
        temperature: float = MUNK_CODE_DEFAULTS.plan.temperature,
    ) -> None:
        self.max_cases = max_cases
        skeleton_output_spec = build_structured_output_spec(GeneratedPlanSkeletonDraft, output_strategy=output_strategy)
        append_output_spec = build_structured_output_spec(GeneratedCaseAppendDraft, output_strategy=output_strategy)
        finalize_output_spec = build_structured_output_spec(GeneratedPlanFinalizeDraft, output_strategy=output_strategy)
        settings = cast(Any, {"temperature": temperature, "max_tokens": max_tokens})
        self._skeleton_agent = Agent[PlanAppKnowledgeDeps, GeneratedPlanSkeletonDraft](
            model=cast(Any, model),
            deps_type=PlanAppKnowledgeDeps,
            output_type=skeleton_output_spec.output_type,
            system_prompt=append_system_prompt_suffix(
                SKELETON_SYSTEM_PROMPT,
                skeleton_output_spec.system_prompt_suffix,
            ),
            name="pydantic_plan_skeleton_agent",
            model_settings=settings,
        )
        self._append_agent = Agent[PlanAppKnowledgeDeps, GeneratedCaseAppendDraft](
            model=cast(Any, model),
            deps_type=PlanAppKnowledgeDeps,
            output_type=append_output_spec.output_type,
            system_prompt=append_system_prompt_suffix(
                APPEND_SYSTEM_PROMPT,
                append_output_spec.system_prompt_suffix,
            ),
            name="pydantic_plan_append_agent",
            model_settings=settings,
        )
        self._finalize_agent = Agent(
            model=cast(Any, model),
            output_type=finalize_output_spec.output_type,
            system_prompt=append_system_prompt_suffix(
                FINALIZE_SYSTEM_PROMPT,
                finalize_output_spec.system_prompt_suffix,
            ),
            name="pydantic_plan_finalize_agent",
            model_settings=settings,
        )
        register_plan_app_knowledge_tools(self._skeleton_agent)
        register_plan_app_knowledge_tools(self._append_agent)

    def create_plan_skeleton(
        self,
        *,
        requirement_input: RequirementInput,
        app_id: str,
        platform: str,
        identity_label: str,
        app_introduction: str,
        knowledge_tools: KnowledgeToolProvider,
        requirement_doc: str,
        technical_doc: str | None = None,
    ) -> GeneratedPlanSkeletonDraft:
        prompt = self._build_skeleton_prompt(
            requirement_input=requirement_input,
            app_id=app_id,
            platform=platform,
            identity_label=identity_label,
            app_introduction=app_introduction,
            knowledge_tools=knowledge_tools,
            requirement_doc=requirement_doc,
            technical_doc=technical_doc,
        )
        result = run_agent_sync_compatible(
            self._skeleton_agent,
            prompt,
            deps=PlanAppKnowledgeDeps(app_id=app_id, knowledge_tools=knowledge_tools),
        )
        return result.output

    def create_change_plan_skeleton(
        self,
        *,
        change_input: ChangePlanInput,
        app_id: str,
        platform: str,
        identity_label: str,
        app_introduction: str,
        knowledge_tools: KnowledgeToolProvider,
        requirement_doc: str | None = None,
        technical_doc: str | None = None,
        previous_report: str | None = None,
        previous_results: list[str] | None = None,
        review_contract: ReviewOrchestrationContract | None = None,
    ) -> GeneratedPlanSkeletonDraft:
        prompt = self._build_change_skeleton_prompt(
            change_input=change_input,
            app_id=app_id,
            platform=platform,
            identity_label=identity_label,
            app_introduction=app_introduction,
            knowledge_tools=knowledge_tools,
            requirement_doc=requirement_doc,
            technical_doc=technical_doc,
            previous_report=previous_report,
            previous_results=previous_results or [],
            review_contract=review_contract,
        )
        result = run_agent_sync_compatible(
            self._skeleton_agent,
            prompt,
            deps=PlanAppKnowledgeDeps(app_id=app_id, knowledge_tools=knowledge_tools),
        )
        return result.output

    def append_case(
        self,
        *,
        requirement_input: RequirementInput,
        app_id: str,
        platform: str,
        identity_label: str,
        app_introduction: str,
        knowledge_tools: KnowledgeToolProvider,
        requirement_doc: str,
        technical_doc: str | None,
        skeleton: GeneratedPlanSkeletonDraft,
        case_index: int,
        existing_cases: list[TestCase],
    ) -> GeneratedCaseAppendDraft:
        prompt = self._build_append_prompt(
            heading=f"Plan the next {platform} test case for the following app and requirement.",
            metadata_lines=self._build_requirement_metadata_lines(
                app_id=app_id,
                platform=platform,
                identity_label=identity_label,
                artifact_path=requirement_input.artifact_path,
                artifact_url=requirement_input.artifact_url,
            ),
            app_introduction=app_introduction,
            knowledge_tools=knowledge_tools,
            requirement_section=requirement_doc,
            technical_section=technical_doc.strip() if technical_doc else "none",
            extra_sections=[
                ("User Command", requirement_input.user_prompt.strip() if requirement_input.user_prompt else "none"),
            ],
            skeleton=skeleton,
            case_index=case_index,
            existing_cases=existing_cases,
        )
        result = run_agent_sync_compatible(
            self._append_agent,
            prompt,
            deps=PlanAppKnowledgeDeps(app_id=app_id, knowledge_tools=knowledge_tools),
        )
        return result.output

    def append_change_case(
        self,
        *,
        change_input: ChangePlanInput,
        app_id: str,
        platform: str,
        identity_label: str,
        app_introduction: str,
        knowledge_tools: KnowledgeToolProvider,
        requirement_doc: str | None,
        technical_doc: str | None,
        previous_report: str | None,
        previous_results: list[str],
        review_contract: ReviewOrchestrationContract | None,
        skeleton: GeneratedPlanSkeletonDraft,
        case_index: int,
        existing_cases: list[TestCase],
    ) -> GeneratedCaseAppendDraft:
        changed_files = ", ".join(change_input.changed_files) if change_input.changed_files else "none"
        diff_text = change_input.diff_text.strip() if change_input.diff_text else "none"
        change_summary = change_input.change_summary.strip() if change_input.change_summary else "none"
        prompt = self._build_append_prompt(
            heading=f"Plan the next {platform} change-driven verification case for the following app and code change.",
            metadata_lines=[
                *self._build_base_metadata_lines(app_id=app_id, platform=platform, identity_label=identity_label),
                f"Max cases: {self.max_cases}",
                f"Change summary: {change_summary}",
                f"Changed files: {changed_files}",
            ],
            app_introduction=app_introduction,
            knowledge_tools=knowledge_tools,
            requirement_section=requirement_doc.strip() if requirement_doc else "none",
            technical_section=technical_doc.strip() if technical_doc else "none",
            extra_sections=[
                ("Previous Report", previous_report.strip() if previous_report else "none"),
                (
                    "Previous Results",
                    "\n\n".join(result.strip() for result in previous_results if result.strip()) or "none",
                ),
                ("Upstream Review", _render_review_contract(review_contract)),
                ("Diff", diff_text),
            ],
            skeleton=skeleton,
            case_index=case_index,
            existing_cases=existing_cases,
        )
        result = run_agent_sync_compatible(
            self._append_agent,
            prompt,
            deps=PlanAppKnowledgeDeps(app_id=app_id, knowledge_tools=knowledge_tools),
        )
        return result.output

    def finalize_plan(
        self,
        *,
        skeleton: GeneratedPlanSkeletonDraft,
        cases: list[TestCase],
    ) -> GeneratedPlanFinalizeDraft:
        prompt = self._build_finalize_prompt(skeleton=skeleton, cases=cases)
        result = self._finalize_agent.run_sync(prompt)
        return result.output

    def _build_skeleton_prompt(
        self,
        *,
        requirement_input: RequirementInput,
        app_id: str,
        platform: str,
        identity_label: str,
        app_introduction: str,
        knowledge_tools: KnowledgeToolProvider,
        requirement_doc: str,
        technical_doc: str | None,
    ) -> str:
        technical_section = technical_doc.strip() if technical_doc else "none"
        return "\n\n".join(
            [
                f"Plan a compact {platform} test plan skeleton for the following app and requirement.",
                "\n".join(
                    self._build_requirement_metadata_lines(
                        app_id=app_id,
                        platform=platform,
                        identity_label=identity_label,
                        artifact_path=requirement_input.artifact_path,
                        artifact_url=requirement_input.artifact_url,
                    )
                ),
                "App Introduction:\n" + app_introduction.strip(),
                "Knowledge Card Catalog:\n" + _build_knowledge_catalog_text(knowledge_tools),
                "Requirement Document:\n" + requirement_doc.strip(),
                "Technical Document:\n" + technical_section,
                "User Command:\n" + (requirement_input.user_prompt.strip() if requirement_input.user_prompt else "none"),
                "\n".join(
                    [
                        "Planning requirements:",
                        "- Set name to a short, human-readable plan title suitable for direct display in a UI.",
                        "- Do not use ids, timestamps, or placeholder names like plan-1.",
                        f"- Set target_case_count to a value between 1 and {self.max_cases}.",
                        "- Keep the plan compact and focused on distinct coverage.",
                        "- Avoid duplicate cases that differ only by wording.",
                        "- Prefer deterministic, human-readable case groupings.",
                        "- Do not generate concrete case bodies in this step.",
                        "- Default to the seeded knowledge card catalog first; use knowledge_search or knowledge_get when you need more precise flow, assertion, or issue details.",
                        "- Prefer screen and flow cards for navigation understanding, but use assertion, issue, policy, or data cards when they materially improve case quality.",
                        "- Do not invent knowledge card details when the catalog is empty or inconclusive.",
                    ]
                ),
            ]
        )

    def _build_change_skeleton_prompt(
        self,
        *,
        change_input: ChangePlanInput,
        app_id: str,
        platform: str,
        identity_label: str,
        app_introduction: str,
        knowledge_tools: KnowledgeToolProvider,
        requirement_doc: str | None,
        technical_doc: str | None,
        previous_report: str | None,
        previous_results: list[str],
        review_contract: ReviewOrchestrationContract | None,
    ) -> str:
        requirement_section = requirement_doc.strip() if requirement_doc else "none"
        technical_section = technical_doc.strip() if technical_doc else "none"
        previous_report_section = previous_report.strip() if previous_report else "none"
        previous_results_section = "\n\n".join(result.strip() for result in previous_results if result.strip()) or "none"
        review_section = _render_review_contract(review_contract)
        changed_files = ", ".join(change_input.changed_files) if change_input.changed_files else "none"
        diff_text = change_input.diff_text.strip() if change_input.diff_text else "none"
        change_summary = change_input.change_summary.strip() if change_input.change_summary else "none"
        return "\n\n".join(
            [
                f"Plan a compact {platform} change-driven verification skeleton for the following app and code change.",
                "\n".join(
                    [
                        *self._build_base_metadata_lines(app_id=app_id, platform=platform, identity_label=identity_label),
                        f"Max cases: {self.max_cases}",
                        f"Change summary: {change_summary}",
                        f"Changed files: {changed_files}",
                    ]
                ),
                "App Introduction:\n" + app_introduction.strip(),
                "Knowledge Card Catalog:\n" + _build_knowledge_catalog_text(knowledge_tools),
                "Requirement Document:\n" + requirement_section,
                "Technical Document:\n" + technical_section,
                "Previous Report:\n" + previous_report_section,
                "Previous Results:\n" + previous_results_section,
                "Upstream Review:\n" + review_section,
                "Diff:\n" + diff_text,
                "\n".join(
                    [
                        "Planning requirements:",
                        "- Set name to a short, human-readable verification plan title suitable for direct display in a UI.",
                        "- Do not use ids, timestamps, or placeholder names like plan-1.",
                        f"- Set target_case_count to a value between 1 and {self.max_cases}.",
                        "- Prioritize changed behaviors and nearby regression risks.",
                        "- Treat upstream review as risk focus and required coverage guidance, not as runtime verdict.",
                        "- Avoid restating the entire requirement; focus on the changed scope.",
                        "- Do not duplicate already-required review cases; focus on supplemental change-driven coverage.",
                        "- Do not generate concrete case bodies in this step.",
                        "- Default to the seeded knowledge card catalog first; use knowledge_search or knowledge_get when you need more precise flow, assertion, or issue details.",
                        "- Prefer screen and flow cards for changed navigation coverage, but pull assertion or issue cards when they better describe the regression risk.",
                        "- Do not invent knowledge card details when the catalog is empty or inconclusive.",
                    ]
                ),
            ]
        )

    def _build_base_metadata_lines(self, *, app_id: str, platform: str, identity_label: str) -> list[str]:
        return [
            f"App ID: {app_id}",
            f"Platform: {platform}",
            identity_label,
        ]

    def _build_requirement_metadata_lines(
        self,
        *,
        app_id: str,
        platform: str,
        identity_label: str,
        artifact_path: Any,
        artifact_url: Any,
    ) -> list[str]:
        return [
            *self._build_base_metadata_lines(app_id=app_id, platform=platform, identity_label=identity_label),
            f"Source artifact path: {artifact_path or 'none'}",
            f"Source artifact url: {artifact_url or 'none'}",
            f"Max cases: {self.max_cases}",
        ]

    def _build_append_prompt(
        self,
        *,
        heading: str,
        metadata_lines: list[str],
        app_introduction: str,
        knowledge_tools: KnowledgeToolProvider,
        requirement_section: str,
        technical_section: str,
        extra_sections: list[tuple[str, str]],
        skeleton: GeneratedPlanSkeletonDraft,
        case_index: int,
        existing_cases: list[TestCase],
    ) -> str:
        sections = [
            heading,
            "\n".join(metadata_lines),
            "App Context Summary:\n" + _summarize_context_text(app_introduction, max_lines=8, max_chars=900),
            "Knowledge Card Catalog:\n" + _build_knowledge_catalog_text(knowledge_tools),
            "Requirement Summary:\n" + _summarize_context_text(requirement_section, max_lines=18, max_chars=1800),
            "Technical Summary:\n" + _summarize_context_text(technical_section, max_lines=14, max_chars=1400),
        ]
        sections.extend(
            f"{title}:\n{_summarize_context_text(body, max_lines=12, max_chars=1200)}"
            for title, body in extra_sections
        )
        sections.extend(
            [
                "Plan Skeleton:\n"
                + "\n".join(
                    [
                        f"Name: {skeleton.name}",
                        f"Summary: {skeleton.summary}",
                        f"Target case count: {skeleton.target_case_count}",
                        f"Current case number to generate: {case_index + 1}",
                    ]
                ),
                "Coverage Summary:\n" + _render_case_coverage_summary(existing_cases),
                "\n".join(
                    [
                        "Case generation requirements:",
                        "- Generate exactly one new case in this step.",
                        "- Keep each case runner_goal directly executable by the current runner.",
                        "- Keep preconditions focused on mandatory setup, not generic advice.",
                        "- Provide at least one expected result, and keep every expected result concrete and observable on the app UI.",
                        "- Use procedure only when a short step outline adds clear value.",
                        "- Set start_mode to 'reset'.",
                        "- Return page_id as null. Do not infer, generate, or guess any page identifier.",
                        "- Default to the seeded knowledge card catalog first; use knowledge_search or knowledge_get when you need more precise flow, assertion, or issue details.",
                        "- Do not invent knowledge card details when the catalog is empty or inconclusive.",
                    ]
                ),
            ]
        )
        return "\n\n".join(sections)

    @staticmethod
    def _build_finalize_prompt(*, skeleton: GeneratedPlanSkeletonDraft, cases: list[TestCase]) -> str:
        return "\n\n".join(
            [
                "Finalize the plan summary for the generated app test plan.",
                "Plan Skeleton:\n"
                + "\n".join(
                    [
                        f"Name: {skeleton.name}",
                        f"Summary: {skeleton.summary}",
                        f"Target case count: {skeleton.target_case_count}",
                    ]
                ),
                "Generated Cases:\n" + _render_existing_cases(cases),
                "\n".join(
                    [
                        "Finalization requirements:",
                        "- Return a concise final summary only.",
                        "- Reflect the generated coverage faithfully.",
                        "- Do not add or rewrite cases.",
                    ]
                ),
            ]
        )


def _render_review_contract(review_contract: ReviewOrchestrationContract | None) -> str:
    if review_contract is None:
        return "none"
    review_hints = review_contract.review_hints
    finding_lines = [
        (
            f"- [{finding.severity}] {finding.title}: {finding.summary}"
            + (
                f" | knowledge_case_ids={', '.join(finding.knowledge_case_ids)}"
                if finding.knowledge_case_ids
                else ""
            )
        )
        for finding in review_hints.high_risk_findings
    ] or ["- none"]
    missing_verification_lines = [f"- {item}" for item in review_hints.missing_verification] or ["- none"]
    required_case_lines = [
        f"- {case.case_id}: {case.title} | runner_goal={case.runner_goal}"
        for case in review_contract.required_cases
    ] or ["- none"]
    advisory_case_lines = [
        f"- {case.title} | intent={case.intent} | runner_goal={case.runner_goal} | expected={'; '.join(case.expected)}"
        for case in review_contract.advisory_cases
    ] or ["- none"]
    return "\n".join(
        [
            "Upstream Review Risk Summary:",
            review_hints.risk_summary.strip() or "none",
            "",
            "Upstream Review High-risk Findings:",
            *finding_lines,
            "",
            "Upstream Review Missing Verification:",
            *missing_verification_lines,
            "",
            "Required Review Cases:",
            *required_case_lines,
            "",
            "Advisory Review Cases:",
            *advisory_case_lines,
        ]
    )


def _build_knowledge_catalog_text(provider: KnowledgeToolProvider) -> str:
    cards = provider.list(limit=12)
    if not cards:
        return "none"
    return "\n".join(f"- {card.card_id} | {card.card_type} | {card.title}" for card in cards)


def _summarize_context_text(text: str, *, max_lines: int, max_chars: int) -> str:
    normalized = text.strip() or "none"
    lines = normalized.splitlines()
    trimmed_lines = lines[:max_lines]
    summary = "\n".join(trimmed_lines).strip()
    if not summary:
        return "none"
    if len(summary) > max_chars:
        summary = summary[: max_chars - 3].rstrip() + "..."
    elif len(lines) > max_lines:
        summary += "\n..."
    return summary


def _render_existing_cases(cases: list[TestCase]) -> str:
    if not cases:
        return "none"
    rendered: list[str] = []
    for case in cases:
        rendered.append(
            "\n".join(
                [
                    f"- Case ID: {case.case_id}",
                    f"  Title: {case.title}",
                    f"  Intent: {case.intent}",
                    f"  Runner goal: {case.runner_goal}",
                    f"  Expected: {'; '.join(case.expected) or 'none'}",
                ]
            )
        )
    return "\n".join(rendered)


def _render_case_coverage_summary(cases: list[TestCase]) -> str:
    if not cases:
        return "none generated yet"
    rendered: list[str] = []
    for index, case in enumerate(cases, start=1):
        rendered.append(
            f"{index}. {case.title} | intent={case.intent} | runner_goal={case.runner_goal} | expected={'; '.join(case.expected)}"
        )
    return "\n".join(rendered)
