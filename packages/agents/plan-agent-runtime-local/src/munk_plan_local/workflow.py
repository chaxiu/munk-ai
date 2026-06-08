from __future__ import annotations

from collections.abc import Callable
from typing import Any

from munk.testing import TestCase

from munk.planning.models import RequirementPlan

from .draft_models import GeneratedCaseAppendDraft, GeneratedPlanFinalizeDraft, GeneratedPlanSkeletonDraft


class PlannerWorkflowService:
    def generate_plan(
        self,
        *,
        plan_id: str,
        app_id: str,
        source: str,
        version: str,
        build_test_case: Callable[[GeneratedCaseAppendDraft], TestCase],
        create_plan_skeleton: Callable[[], GeneratedPlanSkeletonDraft],
        append_case: Callable[[GeneratedPlanSkeletonDraft, int, list[TestCase]], GeneratedCaseAppendDraft],
        finalize_plan: Callable[[GeneratedPlanSkeletonDraft, list[TestCase]], GeneratedPlanFinalizeDraft],
        event_callback: Callable[[str, str | None, dict[str, Any]], None] | None = None,
    ) -> RequirementPlan:
        self._emit(
            event_callback,
            "plan_skeleton_generation_started",
            "starting plan skeleton generation",
            {"plan_id": plan_id, "app_id": app_id},
        )
        skeleton = create_plan_skeleton()
        self._emit(
            event_callback,
            "plan_skeleton_generated",
            "plan skeleton generated",
            {
                "plan_id": plan_id,
                "app_id": app_id,
                "plan_name": skeleton.name,
                "target_case_count": skeleton.target_case_count,
            },
        )
        appended_cases: list[TestCase] = []
        for case_index in range(skeleton.target_case_count):
            self._emit(
                event_callback,
                "plan_case_generation_started",
                "starting plan case generation",
                {
                    "plan_id": plan_id,
                    "app_id": app_id,
                    "case_index": case_index + 1,
                    "target_case_count": skeleton.target_case_count,
                    "completed_case_count": len(appended_cases),
                },
            )
            append_draft = append_case(skeleton, case_index, list(appended_cases))
            case = build_test_case(append_draft)
            appended_cases.append(case)
            self._emit(
                event_callback,
                "plan_case_generated",
                "plan case generated",
                {
                    "plan_id": plan_id,
                    "app_id": app_id,
                    "case_index": case_index + 1,
                    "target_case_count": skeleton.target_case_count,
                    "completed_case_count": len(appended_cases),
                    "case_id": case.case_id,
                    "case_title": case.title,
                },
            )
        self._emit(
            event_callback,
            "plan_finalize_started",
            "starting plan finalization",
            {
                "plan_id": plan_id,
                "app_id": app_id,
                "plan_name": skeleton.name,
                "target_case_count": skeleton.target_case_count,
                "completed_case_count": len(appended_cases),
            },
        )
        finalized = finalize_plan(skeleton, list(appended_cases))
        self._emit(
            event_callback,
            "plan_finalize_completed",
            "plan finalization completed",
            {
                "plan_id": plan_id,
                "app_id": app_id,
                "plan_name": skeleton.name,
                "target_case_count": skeleton.target_case_count,
                "completed_case_count": len(appended_cases),
                "summary": finalized.summary,
            },
        )
        return RequirementPlan(
            plan_id=plan_id,
            name=skeleton.name,
            app_id=app_id,
            source=source,
            version=version,
            cases=appended_cases,
        )

    @staticmethod
    def _emit(
        event_callback: Callable[[str, str | None, dict[str, Any]], None] | None,
        event_type: str,
        message: str | None,
        data: dict[str, Any],
    ) -> None:
        if event_callback is None:
            return
        event_callback(event_type, message, data)
