from __future__ import annotations

from typing import Any

from munk.reviewing.orchestration_models import ReviewOrchestrationContract
from munk.shared_tools import KnowledgeToolProvider
from munk.testing import TestCase

from munk.planning.models import ChangePlanInput, RequirementInput
from munk.services.knowledge import (
    PLAN_CHANGE_KNOWLEDGE_GUIDANCE_LINES,
    PLAN_KNOWLEDGE_GUIDANCE_LINES,
    build_plan_case_recall_query,
    build_plan_change_recall_query,
    build_plan_knowledge_recall_section,
    build_plan_skeleton_recall_query,
)

from .draft_models import GeneratedCaseOutlineDraft, GeneratedPlanSkeletonDraft
from .prompt_rendering import (
    format_numbered_acceptance_criteria,
    format_optional_section,
    render_case_coverage_summary,
    render_existing_cases,
    render_review_contract,
    summarize_context_text,
)

# Keep this tiny: injected into every skeleton/append user prompt.
UI_ONLY_LINES: tuple[str, ...] = (
    "- UI-only: cases must be runnable on device/browser. Rewrite file/annotation/wiring ACs into visible UI outcomes; never inspect source or diff.",
)

SKELETON_SYSTEM_PROMPT = "\n".join(
    [
        "You are a planning agent for app UI testing.",
        "Generate only a compact plan skeleton, not full test cases.",
        "Return a concise name, a concise summary, and case_outlines.",
        "Each case_outlines item must include a distinct human-readable title.",
        "name must be short, human-readable, and suitable for direct UI display.",
        "Do not use generated ids, timestamps, or generic placeholders like plan-1.",
        "case_outlines length must stay within the requested max cases.",
        "Prefer small, distinct, high-value plans with minimal overlap.",
    ]
)

APPEND_SYSTEM_PROMPT = "\n".join(
    [
        "You are a planning agent for app UI testing.",
        "Generate exactly one structured test case body at a time.",
        "The case title and acceptance criteria mapping are fixed by the case charter.",
        "Each case must include intent, runner_goal, and start_mode.",
        "runner_goal must describe one single-case execution objective for the current runner.",
        "preconditions must list only required setup constraints; leave them empty when none exist.",
        "expected must contain at least one user-observable, verifiable outcome; do not use filler text.",
        "procedure is optional and should be omitted unless there is clear value in preserving a short step outline.",
        "Always set start_mode='reset'.",
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


def build_skeleton_prompt(
    *,
    requirement_input: RequirementInput,
    app_id: str,
    platform: str,
    identity_label: str,
    app_introduction: str,
    knowledge_tools: KnowledgeToolProvider,
    requirement_doc: str,
    technical_doc: str | None,
    max_cases: int,
) -> str:
    knowledge_recall_section, _recall = build_plan_knowledge_recall_section(
        knowledge_tools,
        query_text=build_plan_skeleton_recall_query(requirement_doc=requirement_doc),
        app_introduction=app_introduction,
    )
    return "\n\n".join(
        [
            f"Plan a compact {platform} test plan skeleton for the following app and requirement.",
            "\n".join(
                build_requirement_metadata_lines(
                    app_id=app_id,
                    platform=platform,
                    identity_label=identity_label,
                    artifact_path=requirement_input.artifact_path,
                    artifact_url=requirement_input.artifact_url,
                    max_cases=max_cases,
                )
            ),
            "App Introduction:\n" + app_introduction.strip(),
            knowledge_recall_section,
            "Requirement Document:\n" + requirement_doc.strip(),
            "Technical Document:\n" + format_optional_section(technical_doc),
            "User Command:\n" + format_optional_section(requirement_input.user_prompt),
            "\n".join(
                [
                    "Planning requirements:",
                    "- Set name to a short, human-readable plan title suitable for direct display in a UI.",
                    "- Do not use ids, timestamps, or placeholder names like plan-1.",
                    f"- Output case_outlines with 1 to {max_cases} distinct entries.",
                    "- Each case_outlines item must include a distinct title.",
                    "- Keep acceptance_criteria_indices empty for requirement-driven plans.",
                    "- Keep the plan compact and focused on distinct coverage.",
                    "- Avoid duplicate case titles or overlapping coverage.",
                    "- Do not generate concrete case bodies in this step.",
                    *UI_ONLY_LINES,
                    *PLAN_KNOWLEDGE_GUIDANCE_LINES,
                ]
            ),
        ]
    )


def build_change_skeleton_prompt(
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
    max_cases: int,
) -> str:
    change_summary = format_optional_section(change_input.change_summary)
    diff_text = format_optional_section(change_input.diff_text)
    acceptance_criteria = format_numbered_acceptance_criteria(change_input.acceptance_criteria)
    changed_files = ", ".join(change_input.changed_files) if change_input.changed_files else "none"
    knowledge_recall_section, _recall = build_plan_knowledge_recall_section(
        knowledge_tools,
        query_text=build_plan_change_recall_query(
            acceptance_criteria=change_input.acceptance_criteria,
            change_summary=change_summary,
            diff_text=diff_text,
            requirement_doc=requirement_doc,
        ),
        app_introduction=app_introduction,
    )
    return "\n\n".join(
        [
            f"Plan a compact {platform} change-driven verification skeleton for the following app and code change.",
            "\n".join(
                [
                    *build_base_metadata_lines(app_id=app_id, platform=platform, identity_label=identity_label),
                    f"Max cases: {max_cases}",
                    f"Acceptance criteria:\n{acceptance_criteria}",
                    f"Change summary: {change_summary}",
                    f"Changed files: {changed_files}",
                ]
            ),
            "App Introduction:\n" + app_introduction.strip(),
            knowledge_recall_section,
            "Requirement Document:\n" + format_optional_section(requirement_doc),
            "Technical Document:\n" + format_optional_section(technical_doc),
            "Upstream Review:\n" + render_review_contract(review_contract),
            "Diff:\n" + diff_text,
            "\n".join(
                [
                    "Planning requirements:",
                    "- Set name to a short, human-readable verification plan title suitable for direct display in a UI.",
                    "- Do not use ids, timestamps, or placeholder names like plan-1.",
                    f"- Output case_outlines with 1 to {max_cases} distinct entries.",
                    "- Each case_outlines item must include title and acceptance_criteria_indices.",
                    "- Use 0-based acceptance_criteria_indices that refer to the numbered acceptance criteria list.",
                    "- Cover each AC via UI outcomes when possible; never emit a source-inspection case to tick an AC.",
                    "- Avoid duplicate case titles or overlapping verification paths.",
                    "- Prioritize changed behaviors and nearby regression risks.",
                    "- Treat upstream review as risk focus and required coverage guidance, not as runtime verdict.",
                    "- Avoid restating the entire requirement; focus on the changed scope.",
                    "- Do not duplicate already-required review cases; focus on supplemental change-driven coverage.",
                    "- Do not generate concrete case bodies in this step.",
                    *UI_ONLY_LINES,
                    *PLAN_CHANGE_KNOWLEDGE_GUIDANCE_LINES,
                ]
            ),
        ]
    )


def build_append_prompt(
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
    coverage_summary = render_case_coverage_summary(existing_cases)
    knowledge_recall_section, _recall = build_plan_knowledge_recall_section(
        knowledge_tools,
        query_text=build_plan_case_recall_query(
            skeleton_name=skeleton.name,
            skeleton_summary=skeleton.summary,
            requirement_section=requirement_section,
            case_index=case_index,
            coverage_summary=coverage_summary,
        ),
        app_introduction=app_introduction,
    )
    sections = [
        heading,
        "\n".join(metadata_lines),
        "App Context Summary:\n" + summarize_context_text(app_introduction, max_lines=8, max_chars=900),
        knowledge_recall_section,
        "Requirement Summary:\n" + summarize_context_text(requirement_section, max_lines=18, max_chars=1800),
        "Technical Summary:\n" + summarize_context_text(technical_section, max_lines=14, max_chars=1400),
    ]
    sections.extend(
        f"{title}:\n{summarize_context_text(body, max_lines=12, max_chars=1200)}"
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
            "Coverage Summary:\n" + coverage_summary,
            "\n".join(
                [
                    "Case generation requirements:",
                    "- Generate exactly one new case body in this step.",
                    "- Do not change the fixed title from the case charter.",
                    "- Keep each case runner_goal directly executable by the current runner.",
                    "- Keep preconditions focused on mandatory setup, not generic advice.",
                    "- Provide at least one expected result, and keep every expected result concrete and observable on the app UI.",
                    "- Use procedure only when a short step outline adds clear value.",
                    "- Set start_mode to 'reset'.",
                    *UI_ONLY_LINES,
                    *PLAN_KNOWLEDGE_GUIDANCE_LINES,
                ]
            ),
        ]
    )
    return "\n\n".join(sections)


def build_finalize_prompt(*, skeleton: GeneratedPlanSkeletonDraft, cases: list[TestCase]) -> str:
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
            "Generated Cases:\n" + render_existing_cases(cases),
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


def build_base_metadata_lines(*, app_id: str, platform: str, identity_label: str) -> list[str]:
    return [
        f"App ID: {app_id}",
        f"Platform: {platform}",
        identity_label,
    ]


def build_case_charter_lines(
    outline: GeneratedCaseOutlineDraft,
    *,
    include_ac_indices: bool,
) -> list[str]:
    lines = [f"Title (fixed): {outline.title}"]
    if include_ac_indices:
        indices = outline.acceptance_criteria_indices
        lines.append(f"Acceptance criteria indices (fixed): {indices if indices else '[]'}")
    return lines


def build_requirement_metadata_lines(
    *,
    app_id: str,
    platform: str,
    identity_label: str,
    artifact_path: Any,
    artifact_url: Any,
    max_cases: int,
) -> list[str]:
    return [
        *build_base_metadata_lines(app_id=app_id, platform=platform, identity_label=identity_label),
        f"Source artifact path: {artifact_path or 'none'}",
        f"Source artifact url: {artifact_url or 'none'}",
        f"Max cases: {max_cases}",
    ]
