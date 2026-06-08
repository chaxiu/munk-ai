from __future__ import annotations

from collections.abc import Iterable

from munk.agent_base.platform_profile import PlatformRunnerProfile, get_runner_profile


def build_runner_system_prompt(profile: PlatformRunnerProfile | None = None) -> str:
    active_profile = profile or get_runner_profile(None)
    sections = [
        _section("ROLE", [active_profile.role_identity]),
        _section("MISSION", active_profile.mission_lines),
        _section("COMPLETION_CONTRACT", active_profile.completion_contract_lines),
        _section("TOOL_POLICY", active_profile.tool_policy_lines),
        _section("ACTION_BIAS", active_profile.action_bias_lines),
        _section("PLATFORM_NOTES", active_profile.platform_capability_notes),
    ]
    return "\n\n".join(sections)


def build_runner_prompt_preamble() -> str:
    return "\n\n".join(
        [
            _section(
                "TASK",
                [
                    "Choose the single next action for this step from the current case context.",
                    "Use the objective, prepared context, recent history, last outcome, last action feedback, goal progress, screen summary, seeded vision targets, and image together.",
                    "If the seeded vision targets are insufficient, use read tools only for missing evidence before deciding.",
                    "Treat the prepared page knowledge bundle as the primary app knowledge input for this run.",
                    "If the current screen does not satisfy the step precondition, the next action should move toward that precondition page instead of stop.",
                    "If the step depends on before/after comparison and the next action will overwrite the current state, save the baseline facts first.",
                    "If the required target for the current step is not present in the visible targets, do not substitute a semantically similar control.",
                    "When a blocker such as a soft keyboard, popup, dropdown, picker, or modal is present, remove it first with a clear available action and then re-observe before continuing; do not stop only because the blocker exists.",
                    "Use click only for a currently visible numbered target; never use click to simulate back, home, or keyboard dismissal.",
                    "Use long_press only for a currently visible numbered target when the product behavior specifically requires press-and-hold.",
                    "Use back only for the system back event.",
                    "Use input_text only when the intended input already has focus; use clear_and_input when you must target a specific visible input element.",
                    "Use memory tools only for facts worth reusing across later steps; do not turn them into verbose logs.",
                    "If app knowledge is absent or inconclusive, do not invent knowledge card details, page assertions, or flow constraints.",
                ],
            ),
            _section(
                "OUTPUT_REMINDER",
                [
                    "When enough information is available, finish by calling exactly one final structured action output.",
                ],
            ),
        ]
    )


def build_runner_user_prompt(
    *,
    case_brief: str,
    history_summary: str,
    last_outcome: str,
    last_action_feedback: str,
    goal_progress: str,
    screen_summary: str,
    targets_text: str,
    prepared_context_text: str,
    prepared_knowledge_text: str,
    context_prep_fallback_reason: str | None,
    missing_action_attempted: bool,
) -> str:
    objective_lines, procedure_lines = _split_case_brief_sections(case_brief)
    sections: list[str] = [
        build_runner_prompt_preamble(),
        _section("OBJECTIVE", objective_lines),
        _section("PROCEDURE", procedure_lines),
        _section("CONTEXT_PREP", _split_block(prepared_context_text)),
        _section("PAGE_KNOWLEDGE", _split_block(prepared_knowledge_text)),
        _section("HISTORY", [history_summary]),
        _section("LAST_OUTCOME", [last_outcome]),
        _section("LAST_ACTION_FEEDBACK", _split_block(last_action_feedback)),
        _section("GOAL_PROGRESS", _split_block(goal_progress)),
        _section("SCREEN", _split_block(screen_summary)),
        _section("TARGETS", _split_block(targets_text)),
    ]
    if context_prep_fallback_reason is not None:
        sections.append(_section("CONTEXT_PREP_FALLBACK", [context_prep_fallback_reason]))
    retry_block = build_runner_retry_block(missing_action_attempted)
    if retry_block is not None:
        sections.append(retry_block)
    return "\n\n".join(sections)


def build_runner_retry_block(missing_action_attempted: bool) -> str | None:
    if not missing_action_attempted:
        return None
    return _section(
        "RETRY",
        [
            "Previous attempt ended without a valid structured action.",
            "Do not keep exploring with read tools if the existing seeded evidence is already enough.",
            "If the current step target is still absent, do not guess a nearby control; move toward the precondition page or remove blockers, then re-observe and decide.",
            "Do not fall back to click when the intended action is really back or keyboard dismissal.",
            "Do not return JSON strings where a structured object or list is required.",
            "Finish now by calling exactly one final structured action output.",
        ],
    )


def build_runner_seed_context(
    *,
    screen_summary: str,
    targets_text: str,
) -> str:
    return "\n\n".join(
        [
            _section("SCREEN", _split_block(screen_summary)),
            _section("TARGETS", _split_block(targets_text)),
        ]
    )


def _section(name: str, lines: Iterable[str]) -> str:
    clean_lines = [line.rstrip() for line in lines]
    if not clean_lines:
        clean_lines = ["none"]
    return "\n".join([f"[{name}]", *clean_lines])


def _split_block(value: str) -> list[str]:
    lines = [line.rstrip() for line in value.splitlines() if line.strip()]
    return lines or ["none"]


def _split_case_brief_sections(case_brief: str) -> tuple[list[str], list[str]]:
    objective_lines: list[str] = []
    procedure_lines: list[str] = []
    current = objective_lines
    for raw_line in case_brief.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        if line == "Procedure:":
            current = procedure_lines
            continue
        if current is procedure_lines and line.endswith(":"):
            current = objective_lines
        current.append(line)
    return objective_lines or ["none"], procedure_lines or ["- none"]
