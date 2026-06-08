from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from munk.execution.models import CaseExecutionResult, PlanExecutionResult
from munk.planning.models import RequirementPlan
from munk.reporting.models import (
    CaseRepairReport,
    PlanRepairReport,
    PlanRepairTotals,
    ReportOverallVerdict,
)
from munk.testing import TestCase


class PlanReportService:
    def build_report(
        self,
        *,
        plan: RequirementPlan,
        plan_result: PlanExecutionResult,
        case_results: list[CaseExecutionResult],
        report_path: Path,
    ) -> PlanRepairReport:
        case_by_id = {case.case_id: case for case in plan.cases}
        ordered_case_reports = [
            self._build_case_report(case=case_by_id[result.case_id], result=result)
            for result in case_results
            if result.case_id in case_by_id
        ]
        sorted_case_reports = self._sort_case_reports(ordered_case_reports)
        totals = self._build_totals(sorted_case_reports)
        overall_verdict = self._derive_overall_verdict(plan_result)
        return PlanRepairReport(
            app_id=plan.app_id,
            plan_id=plan.plan_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
            overall_verdict=overall_verdict,
            summary=self._build_summary(totals, overall_verdict, plan_result.stopped_early),
            core_case_summary=self._build_core_case_summary(totals, plan_result.stopped_early),
            totals=totals,
            key_failures=[item.case_id for item in sorted_case_reports if item.verdict == "failed"][:5],
            key_inconclusive=[
                item.case_id for item in sorted_case_reports if item.verdict == "inconclusive"
            ][:5],
            case_reports=sorted_case_reports,
            artifacts={
                "plan_execution": str(plan_result.summary_path),
                "report": str(report_path),
            },
        )

    def write_report(self, path: Path, report: PlanRepairReport) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    def _build_case_report(
        self,
        *,
        case: TestCase,
        result: CaseExecutionResult,
    ) -> CaseRepairReport:
        expected_summary = self._build_expected_summary(case)
        observed_summary = self._build_observed_summary(result)
        mismatch_step = self._build_mismatch_step(result)
        return CaseRepairReport(
            case_id=case.case_id,
            title=case.title,
            is_core_case=case.is_core_case,
            verdict=result.verdict,
            execution_status=result.execution.status,
            expected_summary=expected_summary,
            observed_summary=observed_summary,
            mismatch_step=mismatch_step,
            judge_reason=result.judge_reason,
            failure_hypothesis=result.failure_hypothesis,
            missing_evidence=list(result.missing_evidence),
            recommended_artifacts=self._build_recommended_artifacts(result),
            recommended_evidence_ids=self._build_recommended_evidence_ids(result),
            run_dir=result.run_dir,
        )

    @staticmethod
    def _derive_overall_verdict(plan_result: PlanExecutionResult) -> ReportOverallVerdict:
        if plan_result.status == "failed":
            return "failed"
        if plan_result.status in {"inconclusive", "stopped"}:
            return "inconclusive"
        return "passed"

    @staticmethod
    def _build_expected_summary(case: TestCase) -> str:
        if case.expected:
            return " ".join(item.strip() for item in case.expected if item.strip())
        fallback_parts = [case.intent.strip(), case.runner_goal.strip()]
        return " ".join(part for part in fallback_parts if part)

    @staticmethod
    def _build_observed_summary(result: CaseExecutionResult) -> str:
        evidence_summary = _preferred_evidence_summary(result)
        candidates = [
            evidence_summary,
            result.summary,
            result.judge_reason,
            result.execution.last_action_summary,
        ]
        for item in candidates:
            if item and item.strip():
                return item.strip()
        return "No strong observed summary was produced."

    @staticmethod
    def _build_mismatch_step(result: CaseExecutionResult) -> str:
        for evidence_id in result.supporting_evidence_ids:
            if evidence_id.startswith(("event-", "trace-", "screen_diff-", "screen_frame-", "execution", "runner-history")):
                return evidence_id
        for item in result.evidence:
            if item.kind in {"runner_history", "screen_diff", "screen_frame"}:
                return item.evidence_id
        return "unknown"

    @staticmethod
    def _build_recommended_artifacts(result: CaseExecutionResult) -> dict[str, str]:
        preferred_order = ["result", "decision_trace", "log"]
        artifacts: dict[str, str] = {}
        for key in preferred_order:
            value = result.artifacts.get(key)
            if value:
                artifacts[key] = value
        for key, value in result.artifacts.items():
            if key not in artifacts:
                artifacts[key] = value
        return artifacts

    @staticmethod
    def _build_recommended_evidence_ids(result: CaseExecutionResult) -> list[str]:
        if result.supporting_evidence_ids:
            return list(result.supporting_evidence_ids)
        fallback: list[str] = ["execution"]
        runner_history_ids = [
            item.evidence_id
            for item in result.evidence
            if item.kind == "runner_history"
        ]
        runtime_error_log_ids = [
            item.evidence_id
            for item in result.evidence
            if item.kind == "runtime_error_log"
        ]
        screen_diff_ids = [
            item.evidence_id for item in result.evidence if item.kind == "screen_diff"
        ]
        screen_frame_ids = [
            item.evidence_id for item in result.evidence if item.kind == "screen_frame"
        ]
        screenshot_ids = [
            item.evidence_id for item in result.evidence if item.kind == "screenshot"
        ]
        trace_ids = [
            item.evidence_id
            for item in result.evidence
            if item.kind == "decision_trace" and item.evidence_id.startswith("trace-")
        ]
        event_ids = [item.evidence_id for item in result.evidence if item.evidence_id.startswith("event-")]
        fallback.extend(screen_diff_ids[-1:])
        fallback.extend(runtime_error_log_ids[-1:])
        fallback.extend(screenshot_ids[-2:])
        fallback.extend(screen_frame_ids[-2:])
        fallback.extend(runner_history_ids[-1:])
        fallback.extend(trace_ids[-1:])
        fallback.extend(event_ids[-1:])
        seen: set[str] = set()
        ordered: list[str] = []
        for item in fallback:
            if item not in seen:
                seen.add(item)
                ordered.append(item)
        return ordered

    @staticmethod
    def _sort_case_reports(case_reports: list[CaseRepairReport]) -> list[CaseRepairReport]:
        verdict_rank = {"failed": 0, "inconclusive": 1, "passed": 2}
        return sorted(
            case_reports,
            key=lambda item: (
                0 if item.is_core_case else 1,
                verdict_rank[item.verdict],
                item.title,
            ),
        )

    @staticmethod
    def _build_totals(case_reports: list[CaseRepairReport]) -> PlanRepairTotals:
        core_reports = [item for item in case_reports if item.is_core_case]
        return PlanRepairTotals(
            total_cases=len(case_reports),
            passed_cases=sum(1 for item in case_reports if item.verdict == "passed"),
            failed_cases=sum(1 for item in case_reports if item.verdict == "failed"),
            inconclusive_cases=sum(1 for item in case_reports if item.verdict == "inconclusive"),
            core_total_cases=len(core_reports),
            core_failed_cases=sum(1 for item in core_reports if item.verdict == "failed"),
            core_inconclusive_cases=sum(
                1 for item in core_reports if item.verdict == "inconclusive"
            ),
        )

    @staticmethod
    def _build_summary(
        totals: PlanRepairTotals,
        overall_verdict: ReportOverallVerdict,
        stopped_early: bool,
    ) -> str:
        summary = (
            f"Plan finished with {totals.failed_cases} failed, "
            f"{totals.inconclusive_cases} inconclusive, {totals.passed_cases} passed."
        )
        if totals.core_failed_cases:
            summary += f" Core case impact: {totals.core_failed_cases} failed core case."
        elif totals.core_inconclusive_cases:
            summary += (
                f" Core case impact: {totals.core_inconclusive_cases} inconclusive core case."
            )
        else:
            summary += " Core case impact: no core case failures."
        if stopped_early:
            summary += " Execution stopped early."
        if overall_verdict == "passed":
            summary += " Overall verdict passed."
        elif overall_verdict == "failed":
            summary += " Overall verdict failed."
        else:
            summary += " Overall verdict inconclusive."
        return summary

    @staticmethod
    def _build_core_case_summary(totals: PlanRepairTotals, stopped_early: bool) -> str:
        if totals.core_total_cases == 0:
            summary = "No core cases were marked in this plan."
        elif totals.core_failed_cases:
            summary = f"{totals.core_failed_cases} core case failed and requires attention."
        elif totals.core_inconclusive_cases:
            summary = (
                f"{totals.core_inconclusive_cases} core case is inconclusive and should be rechecked."
            )
        else:
            summary = "All executed core cases passed."
        if stopped_early:
            summary += " Plan execution stopped early."
        return summary


def _preferred_evidence_summary(result: CaseExecutionResult) -> str | None:
    preferred_kinds = ("screen_diff", "runtime_error_log", "screen_frame", "runner_history")
    for kind in preferred_kinds:
        for item in result.evidence:
            if item.kind != kind:
                continue
            if item.summary.strip():
                return item.summary.strip()
    return None
