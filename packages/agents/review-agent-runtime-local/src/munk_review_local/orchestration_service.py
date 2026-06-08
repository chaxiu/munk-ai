from __future__ import annotations

import json
import re
from pathlib import Path

from munk.reviewing.models import ReviewResult, SuggestedFollowUpCase
from munk.reviewing.orchestration_models import (
    ReviewAdvisoryCase,
    ReviewCaseBudget,
    ReviewCaseStartState,
    ReviewFindingHint,
    ReviewHintBlock,
    ReviewOrchestrationContract,
    ReviewOrchestrationStatistics,
    ReviewRequiredCase,
)
from munk.reviewing.runtime import ReviewRuntimeResultData
from pydantic import BaseModel, Field


def empty_required_cases() -> list[ReviewRequiredCase]:
    return []


MAX_REQUIRED_REVIEW_CASES = 3
REVIEW_REQUIRED_CASE_MAX_SECONDS = 120.0


class ReviewOrchestrationBundle(BaseModel):
    result_data: ReviewRuntimeResultData
    contract: ReviewOrchestrationContract
    required_cases: list[ReviewRequiredCase] = Field(default_factory=empty_required_cases)
    advisory_cases: list[ReviewAdvisoryCase] = Field(default_factory=list)
    high_priority_case_count: int = 0
    advisory_case_count: int = 0


class ReviewOrchestrationService:
    def load_bundle(self, review_result_path: Path) -> ReviewOrchestrationBundle:
        if not review_result_path.exists():
            raise ValueError(f"review result not found: {review_result_path}")
        payload = json.loads(review_result_path.read_text(encoding="utf-8"))
        review_result = ReviewResult.model_validate(payload)
        return self.build_bundle(
            result_data=self._build_result_data(review_result),
            app_id=review_result.app_id,
        )

    def build_bundle(
        self,
        *,
        result_data: ReviewRuntimeResultData,
        app_id: str | None,
    ) -> ReviewOrchestrationBundle:
        high_priority_cases = [
            item for item in result_data.suggested_follow_up_cases if item.priority == "high"
        ]
        required_cases = [
            self._build_required_case(index=index, suggested_case=item)
            for index, item in enumerate(high_priority_cases[:MAX_REQUIRED_REVIEW_CASES], start=1)
        ]
        advisory_cases = [
            self._build_advisory_case(item)
            for item in result_data.suggested_follow_up_cases
            if item.priority != "high"
        ]
        high_priority_case_count = sum(
            1 for item in result_data.suggested_follow_up_cases if item.priority == "high"
        )
        advisory_case_count = sum(
            1 for item in result_data.suggested_follow_up_cases if item.priority != "high"
        )
        contract = ReviewOrchestrationContract(
            app_id=app_id,
            required_cases=required_cases,
            advisory_cases=advisory_cases,
            review_hints=self._build_review_hints(result_data),
            statistics=ReviewOrchestrationStatistics(
                finding_count=result_data.finding_count,
                high_risk_count=result_data.high_risk_count,
                high_priority_case_count=high_priority_case_count,
                advisory_case_count=advisory_case_count,
            ),
        )
        return ReviewOrchestrationBundle(
            result_data=result_data,
            contract=contract,
            required_cases=required_cases,
            advisory_cases=advisory_cases,
            high_priority_case_count=high_priority_case_count,
            advisory_case_count=advisory_case_count,
        )

    @staticmethod
    def _build_required_case(*, index: int, suggested_case: SuggestedFollowUpCase) -> ReviewRequiredCase:
        return ReviewRequiredCase(
            case_id=f"review-{index}-{_slugify(suggested_case.title)}",
            title=suggested_case.title,
            intent=suggested_case.intent,
            expected=list(suggested_case.expected),
            runner_goal=suggested_case.runner_goal,
            budget=ReviewCaseBudget(max_seconds=REVIEW_REQUIRED_CASE_MAX_SECONDS),
            start_state=ReviewCaseStartState(mode="reset"),
        )

    @staticmethod
    def _build_advisory_case(suggested_case: SuggestedFollowUpCase) -> ReviewAdvisoryCase:
        return ReviewAdvisoryCase(
            title=suggested_case.title,
            intent=suggested_case.intent,
            priority=suggested_case.priority,
            runner_goal=suggested_case.runner_goal,
            expected=list(suggested_case.expected),
            recommended_checks=list(suggested_case.recommended_checks),
            changed_files=list(suggested_case.changed_files),
        )

    @staticmethod
    def _build_review_hints(result_data: ReviewRuntimeResultData) -> ReviewHintBlock:
        related_changed_files = _unique_preserve_order(
            item for finding in result_data.findings for item in finding.changed_files
        )
        if not related_changed_files:
            related_changed_files = _unique_preserve_order(
                item
                for case in result_data.suggested_follow_up_cases
                for item in case.changed_files
            )
        related_knowledge_case_ids = _unique_preserve_order(
            item for finding in result_data.findings for item in finding.knowledge_case_ids
        )
        return ReviewHintBlock(
            risk_summary=result_data.risk_summary,
            likely_regression_surface=list(result_data.likely_regression_surface),
            missing_verification=list(result_data.missing_verification),
            high_risk_findings=[
                ReviewFindingHint(
                    severity=finding.severity,
                    title=finding.title,
                    summary=finding.summary,
                    changed_files=list(finding.changed_files),
                    knowledge_case_ids=list(finding.knowledge_case_ids),
                    recommended_checks=list(finding.recommended_checks),
                )
                for finding in result_data.findings
                if finding.severity in {"high", "critical"}
            ],
            related_changed_files=related_changed_files,
            related_knowledge_case_ids=related_knowledge_case_ids,
        )

    @staticmethod
    def _build_result_data(review_result: ReviewResult) -> ReviewRuntimeResultData:
        return ReviewRuntimeResultData(
            app_id=review_result.app_id,
            risk_summary=review_result.risk_summary,
            likely_regression_surface=list(review_result.likely_regression_surface),
            missing_verification=list(review_result.missing_verification),
            suggested_follow_up_cases=list(review_result.suggested_follow_up_cases),
            findings=list(review_result.findings),
            knowledge_hits=list(review_result.knowledge_hits),
        )


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:40] or "case"


def _unique_preserve_order(values) -> list[str]:  # noqa: ANN001
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered
