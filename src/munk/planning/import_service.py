from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from munk.app_assets.storage import AppRegistry
from munk.planning.models import RequirementPlan
from munk.planning.plan_mutation_service import PlanMutationService
from munk.planning.service import PLAN_VERSION, default_plan_id
from munk.planning.storage import PlanStore
from munk.testing import AiGuidance, CaseBudget, CaseStartState, TestCase

PLAN_IMPORT_SOURCE = "plan_import"


@dataclass(frozen=True)
class PlanImportResult:
    plan: RequirementPlan
    plan_path: str


class PlanImportService:
    def __init__(
        self,
        *,
        plan_store: PlanStore | None = None,
        app_registry: AppRegistry | None = None,
    ) -> None:
        self._plan_store = plan_store or PlanStore()
        self._app_registry = app_registry or AppRegistry(self._plan_store.root_dir)
        self._mutation_service = PlanMutationService(plan_store=self._plan_store)

    def import_plan(
        self,
        *,
        app_id: str,
        name: str,
        raw_plan: dict[str, Any],
        file_name: str | None = None,
    ) -> PlanImportResult:
        normalized_app_id = AppRegistry.normalize_app_id(app_id)
        if not self._app_registry.exists(normalized_app_id):
            raise FileNotFoundError(f"app '{normalized_app_id}' not found")

        cases_data = raw_plan.get("cases")
        if not isinstance(cases_data, list):
            raise ValueError("raw_plan.cases must be a list")
        if not cases_data:
            raise ValueError("raw_plan.cases must not be empty")

        normalized_cases = self._normalize_cases(cases_data)
        plan = RequirementPlan(
            plan_id=default_plan_id(),
            name=name,
            app_id=normalized_app_id,
            source=PLAN_IMPORT_SOURCE,
            version=PLAN_VERSION,
            cases=normalized_cases,
            source_metadata=self._build_source_metadata(raw_plan=raw_plan, file_name=file_name),
        )
        plan_path = self._plan_store.save(plan)
        return PlanImportResult(plan=plan, plan_path=str(plan_path))

    def _normalize_cases(self, cases_data: list[Any]) -> list[TestCase]:
        normalized_cases: list[TestCase] = []
        seen_case_ids: set[str] = set()

        for index, raw_case in enumerate(cases_data, start=1):
            if not isinstance(raw_case, dict):
                raise ValueError(f"raw_plan.cases[{index - 1}] must be an object")
            case_id = self._normalized_case_id(raw_case.get("case_id"), seen_case_ids)
            case = TestCase(
                case_id=case_id,
                title=self._require_case_text(raw_case.get("title"), field_name=f"cases[{index - 1}].title"),
                intent=self._require_case_text(raw_case.get("intent"), field_name=f"cases[{index - 1}].intent"),
                preconditions=self._coerce_text_list(raw_case.get("preconditions"), field_name=f"cases[{index - 1}].preconditions"),
                expected=self._coerce_text_list(raw_case.get("expected"), field_name=f"cases[{index - 1}].expected"),
                procedure=self._coerce_text_list(raw_case.get("procedure"), field_name=f"cases[{index - 1}].procedure"),
                post_action=self._coerce_text_list(raw_case.get("post_action"), field_name=f"cases[{index - 1}].post_action"),
                is_core_case=bool(raw_case.get("is_core_case", False)),
                runner_goal=self._require_case_text(raw_case.get("runner_goal"), field_name=f"cases[{index - 1}].runner_goal"),
                budget=self._coerce_budget(raw_case.get("budget"), field_name=f"cases[{index - 1}].budget"),
                start_state=self._coerce_start_state(raw_case.get("start_state"), field_name=f"cases[{index - 1}].start_state"),
                ai_guidance=self._coerce_ai_guidance(
                    raw_case.get("ai_guidance"),
                    field_name=f"cases[{index - 1}].ai_guidance",
                ),
                source_metadata=self._coerce_source_metadata(
                    raw_case.get("source_metadata"),
                    field_name=f"cases[{index - 1}].source_metadata",
                ),
            )
            self._mutation_service._validate_case(case)  # noqa: SLF001
            normalized_cases.append(case)
            seen_case_ids.add(case_id)
        return normalized_cases

    @staticmethod
    def _normalized_case_id(raw_case_id: Any, seen_case_ids: set[str]) -> str:
        candidate = str(raw_case_id).strip() if raw_case_id is not None else ""
        if not candidate or candidate in seen_case_ids:
            while True:
                candidate = f"case-{uuid4()}"
                if candidate not in seen_case_ids:
                    break
        return candidate

    @staticmethod
    def _require_case_text(value: Any, *, field_name: str) -> str:
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be a non-empty string")
        cleaned = value.strip()
        if not cleaned:
            raise ValueError(f"{field_name} must be a non-empty string")
        return cleaned

    @staticmethod
    def _coerce_text_list(value: Any, *, field_name: str) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError(f"{field_name} must be a list")
        normalized: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise ValueError(f"{field_name} must contain only strings")
            cleaned = item.strip()
            if not cleaned:
                raise ValueError(f"{field_name} must not contain empty items")
            normalized.append(cleaned)
        return normalized

    @classmethod
    def _coerce_budget(cls, value: Any, *, field_name: str) -> CaseBudget | None:
        if value is None:
            return None
        if not isinstance(value, dict):
            raise ValueError(f"{field_name} must be an object")
        try:
            return CaseBudget(
                max_steps=value.get("max_steps"),
                max_seconds=value.get("max_seconds"),
            )
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"{field_name} is invalid: {exc}") from exc

    @classmethod
    def _coerce_start_state(cls, value: Any, *, field_name: str) -> CaseStartState:
        if value is None:
            return CaseStartState(mode="reset", page_id=None)
        if not isinstance(value, dict):
            raise ValueError(f"{field_name} must be an object")
        try:
            return CaseStartState(
                mode=value.get("mode", "reset"),
                page_id=value.get("page_id"),
            )
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"{field_name} is invalid: {exc}") from exc

    @staticmethod
    def _coerce_source_metadata(value: Any, *, field_name: str) -> dict[str, str]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise ValueError(f"{field_name} must be an object")
        normalized: dict[str, str] = {}
        for key, item in value.items():
            if not isinstance(key, str) or not isinstance(item, str):
                raise ValueError(f"{field_name} must contain only string pairs")
            cleaned_key = key.strip()
            cleaned_value = item.strip()
            if not cleaned_key or not cleaned_value:
                raise ValueError(f"{field_name} must not contain empty keys or values")
            normalized[cleaned_key] = cleaned_value
        return normalized

    @classmethod
    def _coerce_ai_guidance(cls, value: Any, *, field_name: str) -> AiGuidance | None:
        if value is None:
            return None
        if not isinstance(value, dict):
            raise ValueError(f"{field_name} must be an object")
        normalized: dict[str, list[str]] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{field_name} must contain only string keys")
            normalized[key] = cls._coerce_text_list(item, field_name=f"{field_name}.{key}")
        try:
            return AiGuidance(**normalized)
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"{field_name} is invalid: {exc}") from exc

    @staticmethod
    def _build_source_metadata(*, raw_plan: dict[str, Any], file_name: str | None) -> dict[str, str]:
        metadata: dict[str, str] = {
            "import_source": PLAN_IMPORT_SOURCE,
        }
        original_plan_id = raw_plan.get("plan_id")
        original_source = raw_plan.get("source")
        original_version = raw_plan.get("version")
        if isinstance(original_plan_id, str) and original_plan_id.strip():
            metadata["original_plan_id"] = original_plan_id.strip()
        if isinstance(original_source, str) and original_source.strip():
            metadata["original_source"] = original_source.strip()
        if isinstance(original_version, str) and original_version.strip():
            metadata["original_version"] = original_version.strip()
        if file_name and file_name.strip():
            metadata["import_file_name"] = file_name.strip()
        return metadata
