from __future__ import annotations

from collections.abc import Iterable

from munk.agent_base.platform_profile import PlatformRunnerProfile, get_runner_profile

def build_runner_system_prompt(profile: PlatformRunnerProfile | None = None) -> str:
    active_profile = profile or get_runner_profile(None)
    sections = [
        _section("ROLE", [active_profile.role_identity]),
        _section("MISSION", active_profile.mission_lines),
        _section("OUTPUT", active_profile.completion_contract_lines),
        _section(
            "RULES",
            [
                *active_profile.tool_policy_lines,
                *active_profile.action_bias_lines,
                *active_profile.platform_capability_notes,
            ],
        ),
    ]
    return "\n\n".join(sections)


def build_runner_prompt_preamble() -> str:
    return _section(
        "TASK",
        [
            "Use OBJECTIVE, PROCEDURE, SCREEN, and TARGETS first for this test step.",
            "Use APP_CONTEXT only as supporting context.",
            "Use read tools only when the seeded evidence is insufficient.",
        ],
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
    missing_action_attempted: bool,
) -> str:
    objective_lines, procedure_lines = _split_case_brief_sections(case_brief)
    sections: list[str] = [
        build_runner_prompt_preamble(),
        _section("OBJECTIVE", objective_lines),
        _section("PROCEDURE", procedure_lines),
        _section("APP_CONTEXT", _split_block(prepared_context_text)),
        _section("HISTORY", [history_summary]),
        _section("LAST_OUTCOME", [last_outcome]),
        _section("LAST_ACTION_FEEDBACK", _split_block(last_action_feedback)),
        _section("GOAL_PROGRESS", _split_block(goal_progress)),
        _section("SCREEN", _split_block(screen_summary)),
        _section("TARGETS", _split_block(targets_text)),
    ]
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
