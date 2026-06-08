from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from munk.agent_base.llm import llm_transcript_scope, summarize_llm_transcript_usage
from munk.agent_runtime.events import AgentRuntimeEventEmitter
from munk.planning.runtime import PlanRuntimeContext, PlanRuntimeOutput, PlanRuntimeResultData
from munk.reviewing.orchestration_models import ReviewOrchestrationContract
from munk.running import validate_case_for_runner
from munk.testing import CaseStartState, TestCase

from munk.config import ResolvedConfig, ResolvedModelConfig, resolve_role_model_config
from munk.planning.models import ChangePlanInput, RequirementInput
from munk.services.errors import (
    ConfigValidationError,
    OperationCancelledError,
    PlanGenerationError,
    RequirementDocumentError,
)

from .agent import PydanticAiPlanAgent
from .draft_models import GeneratedCaseAppendDraft
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
            build_test_case=self._build_test_case,
            create_plan_skeleton=lambda: self._plan_agent.create_plan_skeleton(
                requirement_input=request,
                app_id=runtime_context.app_id,
                platform=runtime_context.platform,
                identity_label=runtime_context.identity_label,
                app_introduction=runtime_context.introduction,
                knowledge_tools=runtime_context.knowledge_tools,
                requirement_doc=requirement_doc,
                technical_doc=technical_doc,
            ),
            append_case=lambda skeleton, case_index, existing_cases: self._plan_agent.append_case(
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
        previous_report = self._read_optional_text_document(request.previous_report_path, kind="previous report")
        previous_results = [self._read_text_document(path, kind="previous result") for path in request.previous_result_paths]
        review_contract = self._load_review_contract(request)
        self._emit_progress(
            event_emitter,
            "change_plan_context_loaded",
            "change plan context loaded",
            {
                "app_id": request.app_id,
                "has_requirement_doc": requirement_doc is not None,
                "has_technical_doc": technical_doc is not None,
                "has_previous_report": previous_report is not None,
                "previous_result_count": len(previous_results),
                "has_review_contract": review_contract is not None,
            },
        )
        self._emit_progress(event_emitter, "plan_agent_ready", "plan agent ready", {"app_id": request.app_id})
        runtime_context = context.app_context
        plan = self._build_workflow_service().generate_plan(
            plan_id=self._plan_id_factory(),
            app_id=request.app_id,
            source="change_driven_plan_agent",
            version="v1.0",
            build_test_case=self._build_test_case,
            create_plan_skeleton=lambda: self._plan_agent.create_change_plan_skeleton(
                change_input=request,
                app_id=runtime_context.app_id,
                platform=runtime_context.platform,
                identity_label=runtime_context.identity_label,
                app_introduction=runtime_context.introduction,
                knowledge_tools=runtime_context.knowledge_tools,
                requirement_doc=requirement_doc,
                technical_doc=technical_doc,
                previous_report=previous_report,
                previous_results=previous_results,
                review_contract=review_contract,
            ),
            append_case=lambda skeleton, case_index, existing_cases: self._plan_agent.append_change_case(
                change_input=request,
                app_id=runtime_context.app_id,
                platform=runtime_context.platform,
                identity_label=runtime_context.identity_label,
                app_introduction=runtime_context.introduction,
                knowledge_tools=runtime_context.knowledge_tools,
                requirement_doc=requirement_doc,
                technical_doc=technical_doc,
                previous_report=previous_report,
                previous_results=previous_results,
                review_contract=review_contract,
                skeleton=skeleton,
                case_index=case_index,
                existing_cases=existing_cases,
            ),
            finalize_plan=lambda skeleton, cases: self._plan_agent.finalize_plan(skeleton=skeleton, cases=cases),
            event_callback=lambda et, msg, data: self._emit_progress(event_emitter, et, msg, data),
        )
        self._write_request_dump(context.managed_paths.request_dump_path, request)
        return plan

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

    def _build_test_case(self, append_draft: GeneratedCaseAppendDraft) -> TestCase:
        case_draft = append_draft.case
        case = TestCase(
            case_id=self._case_id_factory(),
            title=_require_text(case_draft.title, field_name="title"),
            intent=_require_text(case_draft.intent, field_name="intent"),
            preconditions=_clean_text_list(case_draft.preconditions),
            expected=_clean_text_list(case_draft.expected),
            procedure=_clean_text_list(case_draft.procedure),
            runner_goal=_require_text(case_draft.runner_goal, field_name="runner_goal"),
            start_state=CaseStartState(mode=case_draft.start_mode, page_id=_clean_optional_text(case_draft.page_id)),
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


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
