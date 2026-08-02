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

from .draft_models import (
    GeneratedCaseOutlineDraft,
    GeneratedPlanFinalizeDraft,
    GeneratedPlanSkeletonDraft,
    GeneratedTestCaseDraft,
)
from .prompt_builders import (
    APPEND_SYSTEM_PROMPT,
    FINALIZE_SYSTEM_PROMPT,
    SKELETON_SYSTEM_PROMPT,
    build_append_prompt,
    build_base_metadata_lines,
    build_case_charter_lines,
    build_change_skeleton_prompt,
    build_finalize_prompt,
    build_requirement_metadata_lines,
    build_skeleton_prompt,
)
from .prompt_rendering import format_numbered_acceptance_criteria, format_optional_section, render_review_contract
from .shared_tools import PlanAppKnowledgeDeps, register_plan_app_knowledge_tools

PLAN_SKELETON_OUTPUT_RETRIES = 3


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
        append_output_spec = build_structured_output_spec(GeneratedTestCaseDraft, output_strategy=output_strategy)
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
            output_retries=PLAN_SKELETON_OUTPUT_RETRIES,
            model_settings=settings,
        )
        self._append_agent = Agent[PlanAppKnowledgeDeps, GeneratedTestCaseDraft](
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
        prompt = build_skeleton_prompt(
            requirement_input=requirement_input,
            app_id=app_id,
            platform=platform,
            identity_label=identity_label,
            app_introduction=app_introduction,
            knowledge_tools=knowledge_tools,
            requirement_doc=requirement_doc,
            technical_doc=technical_doc,
            max_cases=self.max_cases,
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
        review_contract: ReviewOrchestrationContract | None = None,
    ) -> GeneratedPlanSkeletonDraft:
        prompt = build_change_skeleton_prompt(
            change_input=change_input,
            app_id=app_id,
            platform=platform,
            identity_label=identity_label,
            app_introduction=app_introduction,
            knowledge_tools=knowledge_tools,
            requirement_doc=requirement_doc,
            technical_doc=technical_doc,
            review_contract=review_contract,
            max_cases=self.max_cases,
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
        outline: GeneratedCaseOutlineDraft,
    ) -> GeneratedTestCaseDraft:
        prompt = build_append_prompt(
            heading=f"Plan the next {platform} test case for the following app and requirement.",
            metadata_lines=[
                *build_case_charter_lines(outline, include_ac_indices=False),
                *build_requirement_metadata_lines(
                    app_id=app_id,
                    platform=platform,
                    identity_label=identity_label,
                    artifact_path=requirement_input.artifact_path,
                    artifact_url=requirement_input.artifact_url,
                    max_cases=self.max_cases,
                ),
            ],
            app_introduction=app_introduction,
            knowledge_tools=knowledge_tools,
            requirement_section=requirement_doc,
            technical_section=format_optional_section(technical_doc),
            extra_sections=[("User Command", format_optional_section(requirement_input.user_prompt))],
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
        review_contract: ReviewOrchestrationContract | None,
        skeleton: GeneratedPlanSkeletonDraft,
        case_index: int,
        existing_cases: list[TestCase],
        outline: GeneratedCaseOutlineDraft,
    ) -> GeneratedTestCaseDraft:
        changed_files = ", ".join(change_input.changed_files) if change_input.changed_files else "none"
        prompt = build_append_prompt(
            heading=f"Plan the next {platform} change-driven verification case for the following app and code change.",
            metadata_lines=[
                *build_case_charter_lines(outline, include_ac_indices=True),
                *build_base_metadata_lines(app_id=app_id, platform=platform, identity_label=identity_label),
                f"Max cases: {self.max_cases}",
                f"Acceptance criteria:\n{format_numbered_acceptance_criteria(change_input.acceptance_criteria)}",
                f"Change summary: {format_optional_section(change_input.change_summary)}",
                f"Changed files: {changed_files}",
            ],
            app_introduction=app_introduction,
            knowledge_tools=knowledge_tools,
            requirement_section=format_optional_section(requirement_doc),
            technical_section=format_optional_section(technical_doc),
            extra_sections=[
                ("Upstream Review", render_review_contract(review_contract)),
                ("Diff", format_optional_section(change_input.diff_text)),
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
        result = self._finalize_agent.run_sync(build_finalize_prompt(skeleton=skeleton, cases=cases))
        return result.output
