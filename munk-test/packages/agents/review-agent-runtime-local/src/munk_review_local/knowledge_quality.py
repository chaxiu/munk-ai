from __future__ import annotations

from dataclasses import asdict, dataclass

from munk.reviewing.models import ReviewCaseType

from .knowledge_models import KnowledgeCaseDocument

MIN_BODY_LINES = 16
MIN_RECOMMENDED_CHECKS = 3
MAX_SUMMARY_CHARS = 220
MAX_CHECK_CHARS = 200


@dataclass(frozen=True)
class KnowledgeQualityIssue:
    case_id: str
    rule_id: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class KnowledgeQualityReport:
    issues: tuple[KnowledgeQualityIssue, ...]

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    def to_list(self, *, limit: int | None = None) -> list[dict[str, str]]:
        issues = self.issues if limit is None else self.issues[:limit]
        return [issue.to_dict() for issue in issues]


class KnowledgeQualityValidator:
    def validate_documents(self, documents: list[KnowledgeCaseDocument]) -> KnowledgeQualityReport:
        issues: list[KnowledgeQualityIssue] = []
        for document in documents:
            issues.extend(self.validate_document(document))
        return KnowledgeQualityReport(issues=tuple(issues))

    def validate_document(self, document: KnowledgeCaseDocument) -> list[KnowledgeQualityIssue]:
        manifest = document.manifest
        issues: list[KnowledgeQualityIssue] = []

        non_empty_lines = [line for line in document.body_md.splitlines() if line.strip()]
        if len(non_empty_lines) < MIN_BODY_LINES:
            issues.append(
                self._issue(
                    document.case_id,
                    "body-too-short",
                    f"body.md has {len(non_empty_lines)} non-empty lines; require at least {MIN_BODY_LINES}",
                )
            )

        if len(manifest.summary.strip()) > MAX_SUMMARY_CHARS:
            issues.append(
                self._issue(
                    document.case_id,
                    "summary-too-long",
                    f"summary has {len(manifest.summary.strip())} characters; keep it within {MAX_SUMMARY_CHARS}",
                )
            )

        if len(manifest.recommended_checks) < MIN_RECOMMENDED_CHECKS:
            issues.append(
                self._issue(
                    document.case_id,
                    "insufficient-checks",
                    f"recommended_checks has {len(manifest.recommended_checks)} items; require at least {MIN_RECOMMENDED_CHECKS}",
                )
            )

        for index, check in enumerate(manifest.recommended_checks, start=1):
            if len(check.strip()) > MAX_CHECK_CHARS:
                issues.append(
                    self._issue(
                        document.case_id,
                        "check-too-long",
                        f"recommended_checks[{index}] has {len(check.strip())} characters; split it into smaller review actions",
                    )
                )

        duplicated_tags = sorted(
            tag
            for tag in manifest.tags
            if tag in {str(manifest.platform), manifest.domain, *manifest.code_languages}
        )
        if duplicated_tags:
            issues.append(
                self._issue(
                    document.case_id,
                    "redundant-structural-tags",
                    f"tags repeat structured fields: {', '.join(duplicated_tags)}",
                )
            )

        redundant_case_type_tags = sorted(
            tag
            for tag in manifest.tags
            if tag in {str(manifest.case_type), str(manifest.case_type).replace("_", "-")}
        )
        if redundant_case_type_tags:
            issues.append(
                self._issue(
                    document.case_id,
                    "redundant-case-type-tags",
                    f"tags repeat case_type semantics: {', '.join(redundant_case_type_tags)}",
                )
            )

        required_heading = self._required_heading_for_case_type(manifest.case_type)
        if required_heading not in document.body_md:
            issues.append(
                self._issue(
                    document.case_id,
                    "missing-required-heading",
                    f"body.md for {manifest.case_type} must include heading `{required_heading}`",
                )
            )

        return issues

    @staticmethod
    def _required_heading_for_case_type(case_type: ReviewCaseType) -> str:
        if case_type == "bad_case":
            return "## Diff Signals"
        if case_type == "best_practice":
            return "## Boundaries"
        return "## Mandatory Checks"

    @staticmethod
    def _issue(case_id: str, rule_id: str, message: str) -> KnowledgeQualityIssue:
        return KnowledgeQualityIssue(case_id=case_id, rule_id=rule_id, message=message)
