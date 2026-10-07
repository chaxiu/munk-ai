from __future__ import annotations

from pathlib import Path

VERIFY_CHANGE_MAX_DIFF_CHARS = 65536
VERIFY_CHANGE_MAX_ACCEPTANCE_CRITERIA = 50
VERIFY_CHANGE_MAX_ACCEPTANCE_CRITERION_CHARS = 2048
VERIFY_CHANGE_MAX_ACCEPTANCE_CRITERIA_TOTAL_CHARS = 16384


def normalize_acceptance_criteria(values: list[str] | None) -> list[str]:
    if not values:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        stripped = value.strip()
        if not stripped or stripped in seen:
            continue
        seen.add(stripped)
        normalized.append(stripped)
    return normalized


def has_acceptance_criteria(criteria: list[str]) -> bool:
    return bool(normalize_acceptance_criteria(criteria))


def validate_acceptance_criteria(criteria: list[str] | None) -> list[str]:
    normalized = normalize_acceptance_criteria(criteria)
    if not normalized:
        return []

    actual_count = len(normalized)
    if actual_count > VERIFY_CHANGE_MAX_ACCEPTANCE_CRITERIA:
        raise ValueError(
            "acceptance_criteria exceeds the maximum allowed count: "
            f"actual_count={actual_count}, max_count={VERIFY_CHANGE_MAX_ACCEPTANCE_CRITERIA}."
        )

    total_length = 0
    for index, criterion in enumerate(normalized, start=1):
        criterion_length = len(criterion)
        if criterion_length > VERIFY_CHANGE_MAX_ACCEPTANCE_CRITERION_CHARS:
            raise ValueError(
                "acceptance_criteria item exceeds the maximum allowed length: "
                f"index={index}, actual_length={criterion_length}, "
                f"max_length={VERIFY_CHANGE_MAX_ACCEPTANCE_CRITERION_CHARS}."
            )
        total_length += criterion_length

    if total_length > VERIFY_CHANGE_MAX_ACCEPTANCE_CRITERIA_TOTAL_CHARS:
        raise ValueError(
            "acceptance_criteria exceeds the maximum allowed total length: "
            f"actual_total_length={total_length}, "
            f"max_total_length={VERIFY_CHANGE_MAX_ACCEPTANCE_CRITERIA_TOTAL_CHARS}."
        )

    return normalized


def has_change_planning_context(
    *,
    acceptance_criteria: list[str],
    change_summary: str | None,
    changed_files: list[str],
    diff_text: str | None,
    requirement_doc_path: Path | None,
) -> bool:
    if has_acceptance_criteria(acceptance_criteria):
        return True
    if change_summary is not None and change_summary.strip():
        return True
    if changed_files:
        return True
    if diff_text is not None and diff_text.strip():
        return True
    return requirement_doc_path is not None


def validate_change_planning_intake(
    *,
    enable_plan_agent: bool,
    provided_case_count: int,
    acceptance_criteria: list[str] | None,
    change_summary: str | None,
    changed_files: list[str],
    diff_text: str | None,
    requirement_doc_path: Path | None,
) -> None:
    normalized_criteria = validate_acceptance_criteria(acceptance_criteria)

    if diff_text is not None and diff_text.strip():
        actual_length = len(diff_text)
        if actual_length > VERIFY_CHANGE_MAX_DIFF_CHARS:
            raise ValueError(
                "diff_text exceeds the maximum allowed size for verify change planning: "
                f"actual_length={actual_length}, max_length={VERIFY_CHANGE_MAX_DIFF_CHARS}. "
                "Provide acceptance_criteria, change_summary, provided_cases, or split/summarize "
                "the change upstream before resubmitting."
            )

    if not enable_plan_agent or provided_case_count > 0:
        return

    if has_change_planning_context(
        acceptance_criteria=normalized_criteria,
        change_summary=change_summary,
        changed_files=changed_files,
        diff_text=diff_text,
        requirement_doc_path=requirement_doc_path,
    ):
        return

    raise ValueError(
        "enable_plan_agent requires change context: provide acceptance_criteria, "
        "change_summary, changed_files, diff_text, or requirement_doc_path"
    )
