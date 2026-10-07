from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from uuid import uuid4

from munk.agent_base.llm import llm_transcript_scope, summarize_llm_transcript_usage
from munk.agent_runtime.events import AgentRuntimeEventEmitter
from munk.planning.acceptance_criteria_mapping import (
    find_duplicate_outline_titles,
    find_uncovered_acceptance_criteria_indices,
    normalize_case_acceptance_criteria_indices,
    validate_change_outline_ac_indices,
    validate_plan_case_outlines,
)
from munk.planning.runtime import PlanRuntimeContext, PlanRuntimeOutput, PlanRuntimeResultData
from munk.reviewing.orchestration_models import ReviewOrchestrationContract
from munk.running import validate_case_for_runner
from munk.testing import CaseStartState, TestCase

from munk.config import ResolvedConfig, ResolvedModelConfig, MUNK_CODE_DEFAULTS, resolve_role_model_config
from munk.planning.models import ChangePlanInput, RequirementInput
from munk.services.errors import (
    ConfigValidationError,
    OperationCancelledError,
    PlanGenerationError,
    RequirementDocumentError,
)

from .agent import PydanticAiPlanAgent
from .draft_models import GeneratedCaseOutlineDraft, GeneratedPlanSkeletonDraft, GeneratedTestCaseDraft
from .workflow import PlannerWorkflowService


class PlanRuntimeService:
    def __init__(
        self,
        *,
        resolved_config: ResolvedConfig,
        plan_agent=None,
        plan_id_factory: Callable[[], str] | None = None,  # noqa: ANN001
        case_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._resolved_config = resolved_config
        self._plan_agent = plan_agent or self._build_plan_agent(resolved_config=resolved_config)
        self._plan_id_factory = plan_id_factory or self._default_plan_id
        self._case_id_factory = case_id_factory or self._default_case_id

    def plan(self, request, *, context: PlanRuntimeContext, cancel_controller=None):  # noqa: ANN001
        started_at = self._now_iso()
        emitter = AgentRuntimeEventEmitter(
            agent_role="plan",
            operation_id=context.operation_id,
            event_sink=context.progress,
        )
        emitter.emit_started(message="plan runtime started")
        try:
            with llm_transcript_scope(context.managed_paths.llm_transcript_path):
                if isinstance(request, ChangePlanInput):
                    plan = self._generate_change_plan(
                        request,
                        context=context,
                        cancel_checker=None if cancel_controller is None else cancel_controller.is_cancel_requested,
                        event_emitter=emitter,
                    )
                else:
                    plan = self._generate_plan(
                        request,
                        context=context,
                        cancel_checker=None if cancel_controller is None else cancel_controller.is_cancel_requested,
                        event_emitter=emitter,
                    )
            duration_ms = self._duration_ms(started_at)
            emitter.emit_ended(message="plan runtime completed", data={"plan_id": plan.plan_id, "case_count": len(plan.cases)})
            return PlanRuntimeOutput(
                result_data=PlanRuntimeResultData(plan=plan),
                started_at=started_at,
                duration_ms=duration_ms,
                token_usage=summarize_llm_transcript_usage(context.managed_paths.llm_transcript_path),
            )
        except OperationCancelledError:
            emitter.emit_canceled(message="plan runtime canceled")
            raise
        except Exception as exc:
            emitter.emit_failed(message=str(exc))
            raise

    def _generate_plan(
        self,
        request: RequirementInput,
        *,
        context: PlanRuntimeContext,
        cancel_checker: Callable[[], bool] | None,
        event_emitter: AgentRuntimeEventEmitter,
    ):
        self._raise_if_cancelled(cancel_checker)
        requirement_doc = self._read_text_document(request.requirement_doc_path, kind="requirement document")
        technical_doc = self._read_optional_text_document(request.technical_doc_path, kind="technical document")
        self._emit_progress(
            event_emitter,
            "plan_context_loaded",
            "plan context loaded",
            {
                "app_id": request.app_id,
                "has_technical_doc": technical_doc is not None,
                "assets_root": str(request.assets_root) if request.assets_root is not None else None,
            },
        )
        self._emit_progress(event_emitter, "plan_agent_ready", "plan agent ready", {"app_id": request.app_id})
        runtime_context = context.app_context
        plan = self._build_workflow_service().generate_plan(
            plan_id=self._plan_id_factory(),
            app_id=request.app_id,
            source=request.source_metadata.get("source", "pydantic_plan_agent"),
            version="v1.0",
            build_test_case=partial(self._build_test_case, ac_count=0),
            create_plan_skeleton=lambda: self._validate_requirement_skeleton(
                self._plan_agent.create_plan_skeleton(
                    requirement_input=request,
                    app_id=runtime_context.app_id,
                    platform=runtime_context.platform,
                    identity_label=runtime_context.identity_label,
                    app_introduction=runtime_context.introduction,
                    knowledge_tools=runtime_context.knowledge_tools,
                    requirement_doc=requirement_doc,
                    technical_doc=technical_doc,
                ),
                event_emitter=event_emitter,
            ),
            append_case=lambda skeleton, case_index, existing_cases, outline: self._plan_agent.append_case(
                requirement_input=request,
                app_id=runtime_context.app_id,
                platform=runtime_context.platform,
                identity_label=runtime_context.identity_label,
                app_introduction=runtime_context.introduction,
                knowledge_tools=runtime_context.knowledge_tools,
                requirement_doc=requirement_doc,
                technical_doc=technical_doc,
                skeleton=skeleton,
                case_index=case_index,
                existing_cases=existing_cases,
                outline=outline,
            ),
            finalize_plan=lambda skeleton, cases: self._plan_agent.finalize_plan(skeleton=skeleton, cases=cases),
            event_callback=lambda et, msg, data: self._emit_progress(event_emitter, et, msg, data),
        )
        self._write_request_dump(context.managed_paths.request_dump_path, request)
        return plan

    def _generate_change_plan(
        self,
        request: ChangePlanInput,
        *,
        context: PlanRuntimeContext,
        cancel_checker: Callable[[], bool] | None,
        event_emitter: AgentRuntimeEventEmitter,
    ):
        self._raise_if_cancelled(cancel_checker)
        requirement_doc = self._read_optional_text_document(request.requirement_doc_path, kind="requirement document")
        technical_doc = self._read_optional_text_document(request.technical_doc_path, kind="technical document")
        review_contract = self._load_review_contract(request)
        self._emit_progress(
            event_emitter,
            "change_plan_context_loaded",
            "change plan context loaded",
            {
                "app_id": request.app_id,
                "has_requirement_doc": requirement_doc is not None,
                "has_technical_doc": technical_doc is not None,
                "has_review_contract": review_contract is not None,
            },
        )
        self._emit_progress(event_emitter, "plan_agent_ready", "plan agent ready", {"app_id": request.app_id})
        runtime_context = context.app_context
        ac_count = len(request.acceptance_criteria)
        plan = self._build_workflow_service().generate_plan(
            plan_id=self._plan_id_factory(),
            app_id=request.app_id,
            source="change_driven_plan_agent",
            version="v1.0",
            build_test_case=partial(self._build_test_case, ac_count=ac_count),
            create_plan_skeleton=lambda: self._validate_change_skeleton(
                self._plan_agent.create_change_plan_skeleton(
                    change_input=request,
                    app_id=runtime_context.app_id,
                    platform=runtime_context.platform,
                    identity_label=runtime_context.identity_label,
                    app_introduction=runtime_context.introduction,
                    knowledge_tools=runtime_context.knowledge_tools,
                    requirement_doc=requirement_doc,
                    technical_doc=technical_doc,
                    review_contract=review_contract,
                ),
                acceptance_criteria=request.acceptance_criteria,
                event_emitter=event_emitter,
            ),
            append_case=lambda skeleton, case_index, existing_cases, outline: self._plan_agent.append_change_case(
                change_input=request,
                app_id=runtime_context.app_id,
                platform=runtime_context.platform,
                identity_label=runtime_context.identity_label,
                app_introduction=runtime_context.introduction,
                knowledge_tools=runtime_context.knowledge_tools,
                requirement_doc=requirement_doc,
                technical_doc=technical_doc,
                review_contract=review_contract,
                skeleton=skeleton,
                case_index=case_index,
                existing_cases=existing_cases,
                outline=outline,
            ),
            finalize_plan=lambda skeleton, cases: self._plan_agent.finalize_plan(skeleton=skeleton, cases=cases),
            event_callback=lambda et, msg, data: self._emit_progress(event_emitter, et, msg, data),
        )
        self._write_request_dump(context.managed_paths.request_dump_path, request)
        return plan.model_copy(update={"acceptance_criteria": list(request.acceptance_criteria)})

    def _build_plan_agent(self, *, resolved_config: ResolvedConfig):
        plan_config = self._resolve_plan_section(resolved_config)
        from munk.agent_base.output_strategy import resolve_output_strategy
        from munk.agent_base.pydantic_model_factory import build_pydantic_ai_model

        model = build_pydantic_ai_model(plan_config, config=resolved_config.config)
        return PydanticAiPlanAgent(model=model, output_strategy=resolve_output_strategy(plan_config))

    @staticmethod
    def _resolve_plan_section(resolved_config: ResolvedConfig) -> ResolvedModelConfig:
        plan_config = resolve_role_model_config(resolved_config.config, role="plan")
        if plan_config is None:
            raise ConfigValidationError("config must include a valid LLM model configuration")
        return plan_config

    @staticmethod
    def _build_workflow_service() -> PlannerWorkflowService:
        return PlannerWorkflowService()

    @staticmethod
    def _load_review_contract(request: ChangePlanInput) -> ReviewOrchestrationContract | None:
        if request.review_orchestration_path is None:
            return None
        return ReviewOrchestrationContract.model_validate_json(request.review_orchestration_path.read_text(encoding="utf-8"))

    @staticmethod
    def _read_text_document(path: Path, *, kind: str) -> str:
        if not path.exists():
            raise RequirementDocumentError(f"{kind} not found: {path}")
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            raise RequirementDocumentError(f"{kind} is empty: {path}")
        return text

    def _read_optional_text_document(self, path: Path | None, *, kind: str) -> str | None:
        if path is None:
            return None
        return self._read_text_document(path, kind=kind)

    @staticmethod
    def _write_request_dump(path: Path, request: RequirementInput | ChangePlanInput) -> None:
        path.write_text(request.model_dump_json(indent=2), encoding="utf-8")

    @staticmethod
    def _raise_if_cancelled(cancel_checker: Callable[[], bool] | None) -> None:
        if cancel_checker is not None and cancel_checker():
            raise OperationCancelledError("operation cancelled cooperatively")

    def _plan_agent_max_cases(self) -> int:
        return getattr(self._plan_agent, "max_cases", MUNK_CODE_DEFAULTS.plan.max_cases)

    def _validate_requirement_skeleton(
        self,
        skeleton: GeneratedPlanSkeletonDraft,
        *,
        event_emitter: AgentRuntimeEventEmitter,
    ) -> GeneratedPlanSkeletonDraft:
        try:
            validate_plan_case_outlines(
                skeleton.case_outlines,
                max_cases=self._plan_agent_max_cases(),
            )
        except ValueError as exc:
            raise PlanGenerationError(str(exc)) from exc
        duplicates = find_duplicate_outline_titles(skeleton.case_outlines)
        if duplicates:
            self._emit_progress(
                event_emitter,
                "plan_skeleton_outline_warning",
                "duplicate case outline titles detected",
                {"duplicate_titles": duplicates},
            )
        return skeleton

    def _validate_change_skeleton(
        self,
        skeleton: GeneratedPlanSkeletonDraft,
        *,
        acceptance_criteria: list[str],
        event_emitter: AgentRuntimeEventEmitter,
    ) -> GeneratedPlanSkeletonDraft:
        try:
            validate_plan_case_outlines(
                skeleton.case_outlines,
                max_cases=self._plan_agent_max_cases(),
            )
            validate_change_outline_ac_indices(
                skeleton.case_outlines,
                ac_count=len(acceptance_criteria),
            )
        except ValueError as exc:
            raise PlanGenerationError(str(exc)) from exc
        duplicates = find_duplicate_outline_titles(skeleton.case_outlines)
        if duplicates:
            self._emit_progress(
                event_emitter,
                "plan_skeleton_outline_warning",
                "duplicate case outline titles detected",
                {"duplicate_titles": duplicates},
            )
        uncovered = find_uncovered_acceptance_criteria_indices(
            skeleton.case_outlines,
            ac_count=len(acceptance_criteria),
        )
        if uncovered:
            self._emit_progress(
                event_emitter,
                "plan_skeleton_ac_coverage_warning",
                "acceptance criteria not covered by case outlines",
                {"uncovered_indices": uncovered},
            )
        return skeleton

    def _build_test_case(
        self,
        case_draft: GeneratedTestCaseDraft,
        outline: GeneratedCaseOutlineDraft,
        *,
        ac_count: int = 0,
    ) -> TestCase:
        case = TestCase(
            case_id=self._case_id_factory(),
            title=_require_text(outline.title, field_name="title"),
            intent=_require_text(case_draft.intent, field_name="intent"),
            preconditions=_clean_text_list(case_draft.preconditions),
            expected=_clean_text_list(case_draft.expected),
            procedure=_clean_text_list(case_draft.procedure),
            runner_goal=_require_text(case_draft.runner_goal, field_name="runner_goal"),
            # page_id is Host-owned (navigators / app assets), never planner-filled.
            start_state=CaseStartState(mode=case_draft.start_mode, page_id=None),
            acceptance_criteria_indices=normalize_case_acceptance_criteria_indices(
                outline.acceptance_criteria_indices,
                ac_count=ac_count,
            ),
        )
        try:
            validate_case_for_runner(case)
        except ValueError as exc:
            raise PlanGenerationError(f"generated case is invalid: {exc}") from exc
        return case

    @staticmethod
    def _emit_progress(event_emitter: AgentRuntimeEventEmitter, event_type: str, message: str | None, data: dict[str, object]) -> None:
        event_emitter.emit_progress(event_type=event_type, message=message, data=data)

    @staticmethod
    def _default_plan_id() -> str:
        return f"plan-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    @staticmethod
    def _default_case_id() -> str:
        return str(uuid4())

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _duration_ms(started_at: str) -> int:
        start = datetime.fromisoformat(started_at)
        return max(0, int((datetime.now(timezone.utc) - start).total_seconds() * 1000))


def _require_text(value: str, *, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise PlanGenerationError(f"generated case field '{field_name}' must not be empty")
    return cleaned


def _clean_text_list(values: list[str]) -> list[str]:
    return [item.strip() for item in values if item.strip()]
