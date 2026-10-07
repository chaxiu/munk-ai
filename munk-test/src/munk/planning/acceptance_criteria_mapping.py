from __future__ import annotations

from typing import Literal

from munk.execution.models import JudgeVerdict
from munk.testing import TestCase

CoverageVerdict = Literal["passed", "failed", "inconclusive", "uncovered"]


def normalize_case_acceptance_criteria_indices(
    indices: list[int] | None,
    *,
    ac_count: int,
) -> list[int]:
    if not indices or ac_count <= 0:
        return []
    normalized: list[int] = []
    seen: set[int] = set()
    for index in indices:
        if not isinstance(index, int) or index < 0 or index >= ac_count or index in seen:
            continue
        seen.add(index)
        normalized.append(index)
    normalized.sort()
    return normalized


def validate_plan_case_outlines(
    outlines: list[object],
    *,
    max_cases: int,
) -> None:
    if not outlines:
        raise ValueError("case_outlines must not be empty")
    if len(outlines) > max_cases:
        raise ValueError(
            "case_outlines exceeds the maximum allowed count: "
            f"actual_count={len(outlines)}, max_count={max_cases}."
        )
    for index, outline in enumerate(outlines, start=1):
        title = getattr(outline, "title", None)
        if not isinstance(title, str) or not title.strip():
            raise ValueError(f"case_outlines[{index - 1}].title must not be empty")


def find_duplicate_outline_titles(outlines: list[object]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for outline in outlines:
        title = getattr(outline, "title", "")
        if not isinstance(title, str):
            continue
        normalized = title.strip().casefold()
        if not normalized:
            continue
        if normalized in seen and title.strip() not in duplicates:
            duplicates.append(title.strip())
        seen.add(normalized)
    return duplicates


def find_uncovered_acceptance_criteria_indices(
    outlines: list[object],
    *,
    ac_count: int,
) -> list[int]:
    if ac_count <= 0:
        return []
    covered: set[int] = set()
    for outline in outlines:
        indices = getattr(outline, "acceptance_criteria_indices", [])
        if isinstance(indices, list):
            covered.update(normalize_case_acceptance_criteria_indices(indices, ac_count=ac_count))
    return [index for index in range(ac_count) if index not in covered]


def validate_change_outline_ac_indices(
    outlines: list[object],
    *,
    ac_count: int,
) -> list[int]:
    if ac_count <= 0:
        return []
    for outline_index, outline in enumerate(outlines, start=1):
        indices = getattr(outline, "acceptance_criteria_indices", [])
        if not isinstance(indices, list):
            raise ValueError(f"case_outlines[{outline_index - 1}].acceptance_criteria_indices must be a list")
        normalized = normalize_case_acceptance_criteria_indices(indices, ac_count=ac_count)
        raw_non_empty = [item for item in indices if isinstance(item, int)]
        if raw_non_empty and not normalized:
            raise ValueError(
                f"case_outlines[{outline_index - 1}] has invalid acceptance_criteria_indices for ac_count={ac_count}."
            )
    return find_uncovered_acceptance_criteria_indices(outlines, ac_count=ac_count)


def resolve_acceptance_criteria_texts(
    indices: list[int],
    acceptance_criteria: list[str],
) -> list[str]:
    resolved: list[str] = []
    for index in indices:
        if 0 <= index < len(acceptance_criteria):
            resolved.append(acceptance_criteria[index])
    return resolved


def _rollup_verdict(verdicts: list[JudgeVerdict]) -> CoverageVerdict:
    if not verdicts:
        return "uncovered"
    if any(item == "failed" for item in verdicts):
        return "failed"
    if any(item == "inconclusive" for item in verdicts):
        return "inconclusive"
    return "passed"


def build_acceptance_criteria_coverage(
    *,
    acceptance_criteria: list[str],
    cases: list[TestCase],
    case_verdicts: dict[str, JudgeVerdict],
) -> list[dict[str, object]]:
    if not acceptance_criteria:
        return []

    coverage: list[dict[str, object]] = []
    for index, criterion in enumerate(acceptance_criteria):
        case_ids = [
            case.case_id
            for case in cases
            if index in case.acceptance_criteria_indices
        ]
        verdicts = [case_verdicts[case_id] for case_id in case_ids if case_id in case_verdicts]
        coverage.append(
            {
                "index": index,
                "criterion": criterion,
                "case_ids": case_ids,
                "verdict": _rollup_verdict(verdicts),
            }
        )
    return coverage
