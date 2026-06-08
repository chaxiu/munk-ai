from __future__ import annotations

from dataclasses import dataclass

from munk.planning.models import RequirementPlan
from munk.planning.storage import PlanStore
from munk.running import validate_case_for_runner
from munk.testing import AiGuidance, TestCase


@dataclass(frozen=True)
class CaseMutationResult:
    plan: RequirementPlan
    case: TestCase


@dataclass(frozen=True)
class CaseDeleteResult:
    plan: RequirementPlan
    case_id: str


class PlanMutationService:
    def __init__(self, *, plan_store: PlanStore | None = None) -> None:
        self._plan_store = plan_store or PlanStore()

    def add_case(self, app_id: str, plan_id: str, case: TestCase) -> CaseMutationResult:
        plan = self._load_plan_or_raise(app_id, plan_id)
        self._validate_case(case)
        self._ensure_case_id_unique(plan, case.case_id)
        updated_plan = plan.model_copy(update={"cases": [*plan.cases, case]})
        self._plan_store.save(updated_plan)
        return CaseMutationResult(plan=updated_plan, case=case)

    def replace_case(self, app_id: str, plan_id: str, case_id: str, case: TestCase) -> CaseMutationResult:
        plan = self._load_plan_or_raise(app_id, plan_id)
        if case.case_id != case_id:
            raise ValueError("payload case_id must match route case_id")
        self._validate_case(case)
        case_index = self._find_case_index(plan, case_id)
        self._ensure_case_id_unique(plan, case.case_id, excluding_case_id=case_id)
        updated_cases = list(plan.cases)
        updated_cases[case_index] = case
        updated_plan = plan.model_copy(update={"cases": updated_cases})
        self._plan_store.save(updated_plan)
        return CaseMutationResult(plan=updated_plan, case=case)

    def update_ai_guidance_fields(
        self,
        app_id: str,
        plan_id: str,
        case_id: str,
        *,
        replace_fields: dict[str, list[str]],
    ) -> CaseMutationResult:
        plan = self._load_plan_or_raise(app_id, plan_id)
        case_index = self._find_case_index(plan, case_id)
        current_case = plan.cases[case_index]
        current_guidance = current_case.ai_guidance or AiGuidance()
        updated_guidance = current_guidance.model_copy(update=replace_fields)
        updated_case = current_case.model_copy(update={"ai_guidance": updated_guidance})
        self._validate_case(updated_case)
        updated_cases = list(plan.cases)
        updated_cases[case_index] = updated_case
        updated_plan = plan.model_copy(update={"cases": updated_cases})
        self._plan_store.save(updated_plan)
        return CaseMutationResult(plan=updated_plan, case=updated_case)

    def delete_case(self, app_id: str, plan_id: str, case_id: str) -> CaseDeleteResult:
        plan = self._load_plan_or_raise(app_id, plan_id)
        case_index = self._find_case_index(plan, case_id)
        updated_cases = [item for index, item in enumerate(plan.cases) if index != case_index]
        updated_plan = plan.model_copy(update={"cases": updated_cases})
        self._plan_store.save(updated_plan)
        return CaseDeleteResult(plan=updated_plan, case_id=case_id)

    def reorder_cases(self, app_id: str, plan_id: str, ordered_case_ids: list[str]) -> RequirementPlan:
        plan = self._load_plan_or_raise(app_id, plan_id)
        updated_plan = plan.model_copy(update={"cases": self._reordered_cases(plan, ordered_case_ids)})
        self._plan_store.save(updated_plan)
        return updated_plan

    def _load_plan_or_raise(self, app_id: str, plan_id: str) -> RequirementPlan:
        return self._plan_store.load(app_id, plan_id)

    def _validate_case(self, case: TestCase) -> None:
        if not case.case_id.strip():
            raise ValueError("case case_id must not be empty")
        validate_case_for_runner(case)
        self._validate_text_items(case.preconditions, field_name="preconditions")
        self._validate_text_items(case.expected, field_name="expected")
        self._validate_text_items(case.procedure, field_name="procedure")
        self._validate_text_items(case.post_action, field_name="post_action")
        self._validate_guidance_items(case.ai_guidance)

    @staticmethod
    def _validate_text_items(items: list[str], *, field_name: str) -> None:
        if any(not item.strip() for item in items):
            raise ValueError(f"{field_name} must not contain empty items")

    def _validate_guidance_items(self, guidance: AiGuidance | None) -> None:
        if guidance is None:
            return
        for field_name in AiGuidance.model_fields:
            self._validate_text_items(list(getattr(guidance, field_name)), field_name=f"ai_guidance.{field_name}")

    @staticmethod
    def _ensure_case_id_unique(
        plan: RequirementPlan,
        case_id: str,
        *,
        excluding_case_id: str | None = None,
    ) -> None:
        for existing in plan.cases:
            if excluding_case_id is not None and existing.case_id == excluding_case_id:
                continue
            if existing.case_id == case_id:
                raise ValueError(f"case '{case_id}' already exists in plan '{plan.app_id}/{plan.plan_id}'")

    @staticmethod
    def _find_case_index(plan: RequirementPlan, case_id: str) -> int:
        index = next((index for index, item in enumerate(plan.cases) if item.case_id == case_id), None)
        if index is None:
            raise LookupError(f"case '{case_id}' not found in plan '{plan.app_id}/{plan.plan_id}'")
        return index

    @staticmethod
    def _reordered_cases(plan: RequirementPlan, ordered_case_ids: list[str]) -> list[TestCase]:
        current_case_ids = [case.case_id for case in plan.cases]
        if len(ordered_case_ids) != len(current_case_ids):
            raise ValueError("case_ids must include every case in the plan exactly once")
        if len(set(ordered_case_ids)) != len(ordered_case_ids):
            raise ValueError("case_ids must not contain duplicates")
        if set(ordered_case_ids) != set(current_case_ids):
            raise ValueError("case_ids must match the current plan cases exactly")
        case_by_id = {case.case_id: case for case in plan.cases}
        return [case_by_id[case_id] for case_id in ordered_case_ids]
