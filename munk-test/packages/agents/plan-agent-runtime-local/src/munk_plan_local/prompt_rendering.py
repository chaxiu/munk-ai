from __future__ import annotations

from munk.reviewing.orchestration_models import ReviewOrchestrationContract
from munk.testing import TestCase


def render_review_contract(review_contract: ReviewOrchestrationContract | None) -> str:
    if review_contract is None:
        return "none"
    review_hints = review_contract.review_hints
    finding_lines = _render_review_finding_lines(review_hints.high_risk_findings)
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


def summarize_context_text(text: str, *, max_lines: int, max_chars: int) -> str:
    normalized = text.strip() or "none"
    lines = normalized.splitlines()
    trimmed_lines = lines[:max_lines]
    summary = "\n".join(trimmed_lines).strip()
    if not summary:
        return "none"
    if len(summary) > max_chars:
        return summary[: max_chars - 3].rstrip() + "..."
    if len(lines) > max_lines:
        return summary + "\n..."
    return summary


def render_existing_cases(cases: list[TestCase]) -> str:
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


def render_case_coverage_summary(cases: list[TestCase]) -> str:
    if not cases:
        return "none generated yet"
    rendered: list[str] = []
    for index, case in enumerate(cases, start=1):
        rendered.append(
            f"{index}. {case.title} | intent={case.intent} | runner_goal={case.runner_goal} | expected={'; '.join(case.expected)}"
        )
    return "\n".join(rendered)


def format_numbered_acceptance_criteria(criteria: list[str]) -> str:
    if not criteria:
        return "none"
    return "\n".join(f"{index}: {criterion}" for index, criterion in enumerate(criteria))


def format_optional_section(text: str | None) -> str:
    return text.strip() if text else "none"


def _render_review_finding_lines(findings: list[object]) -> list[str]:
    rendered: list[str] = []
    for finding in findings:
        knowledge_case_ids = getattr(finding, "knowledge_case_ids", None)
        suffix = f" | knowledge_case_ids={', '.join(knowledge_case_ids)}" if knowledge_case_ids else ""
        rendered.append(f"- [{finding.severity}] {finding.title}: {finding.summary}{suffix}")
    return rendered or ["- none"]
