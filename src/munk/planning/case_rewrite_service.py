from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Protocol, cast

from pydantic import BaseModel, Field, field_validator
from pydantic_ai import Agent

from munk.agent_base.llm import run_agent_sync_compatible
from munk.agent_base.output_strategy import (
    append_system_prompt_suffix,
    build_structured_output_spec,
    resolve_output_strategy,
)
from munk.agent_base.pydantic_model_factory import build_pydantic_ai_model
from munk.app_assets.models import AppProfile
from munk.app_assets.storage import AppRegistry
from munk.config import MUNK_CODE_DEFAULTS, ResolvedConfig, resolve_role_model_config
from munk.config.load import load_config_context
from munk.config.schema import OutputStrategy
from munk.planning.storage import PlanStore
from munk.running import validate_case_for_runner
from munk.testing import CaseBudget, CaseStartState, TestCase

_SYSTEM_PROMPT = "\n".join(
    [
        "You are an AI assistant that rewrites UI test cases.",
        "Improve clarity, coverage, and executability without changing the business goal.",
        "Keep the same validation intent unless the user prompt explicitly requests a refinement.",
        "Preserve start-state and budget semantics unless there is a clear reason to adjust them.",
        "Use concise, human-readable wording.",
        "Return only structured output.",
    ]
)


class CaseRewriteDraft(BaseModel):
    title: str
    intent: str
    runner_goal: str
    preconditions: list[str] | None = None
    expected: list[str] | None = None
    procedure: list[str] | None = None
    post_action: list[str] | None = None
    is_core_case: bool | None = None
    start_mode: str | None = None
    start_page_id: str | None = None
    max_steps: int | None = Field(default=None, gt=0)
    max_seconds: float | None = Field(default=None, gt=0)

    @field_validator("title", "intent", "runner_goal")
    @classmethod
    def _validate_required_text(cls, value: str, info) -> str:  # type: ignore[no-untyped-def]
        cleaned = value.strip()
        if not cleaned:
            raise ValueError(f"{info.field_name} must not be empty")
        return cleaned

    @field_validator("preconditions", "expected", "procedure", "post_action")
    @classmethod
    def _validate_text_items(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned_items = [item.strip() for item in value]
        if any(not item for item in cleaned_items):
            raise ValueError("list fields must not contain empty items")
        return cleaned_items

    @field_validator("start_mode")
    @classmethod
    def _validate_start_mode(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if cleaned not in {"reset", "resume"}:
            raise ValueError("start_mode must be 'reset' or 'resume'")
        return cleaned

    @field_validator("start_page_id")
    @classmethod
    def _validate_start_page_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class CaseRewriteAgent(Protocol):
    def rewrite_case(
        self,
        *,
        app_profile: AppProfile | None,
        app_introduction: str | None,
        current_case: TestCase,
        user_prompt: str,
    ) -> CaseRewriteDraft: ...


class PydanticAiCaseRewriteAgent:
    def __init__(
        self,
        *,
        model: object,
        output_strategy: OutputStrategy = "auto",
        max_tokens: int = MUNK_CODE_DEFAULTS.plan.max_tokens,
        temperature: float = MUNK_CODE_DEFAULTS.plan.temperature,
    ) -> None:
        settings = cast(Any, {"temperature": temperature, "max_tokens": max_tokens})
        output_spec = build_structured_output_spec(CaseRewriteDraft, output_strategy=output_strategy)
        self._agent = Agent(
            model=cast(Any, model),
            output_type=output_spec.output_type,
            system_prompt=append_system_prompt_suffix(_SYSTEM_PROMPT, output_spec.system_prompt_suffix),
            name="pydantic_case_rewrite_agent",
            model_settings=settings,
        )

    def rewrite_case(
        self,
        *,
        app_profile: AppProfile | None,
        app_introduction: str | None,
        current_case: TestCase,
        user_prompt: str,
    ) -> CaseRewriteDraft:
        prompt = self._build_prompt(
            app_profile=app_profile,
            app_introduction=app_introduction,
            current_case=current_case,
            user_prompt=user_prompt,
        )
        result = run_agent_sync_compatible(self._agent, prompt)
        return cast(CaseRewriteDraft, result.output)

    @staticmethod
    def _build_prompt(
        *,
        app_profile: AppProfile | None,
        app_introduction: str | None,
        current_case: TestCase,
        user_prompt: str,
    ) -> str:
        app_profile_lines = ["none"]
        if app_profile is not None:
            app_profile_lines = [
                f"app_id: {app_profile.app_id}",
                f"platform: {app_profile.platform}",
                f"target: {app_profile.to_app_target().model_dump_json(indent=2)}",
            ]
        budget = current_case.budget or CaseBudget()
        prompt_lines = [
            "[USER_PROMPT]",
            user_prompt.strip(),
            "",
            "[APP_PROFILE]",
            *app_profile_lines,
            "",
            "[APP_INTRODUCTION]",
            (app_introduction or "none").strip() or "none",
            "",
            "[CURRENT_CASE]",
            f"title: {current_case.title}",
            f"intent: {current_case.intent}",
            f"runner_goal: {current_case.runner_goal}",
            f"preconditions: {current_case.preconditions}",
            f"expected: {current_case.expected}",
            f"procedure: {current_case.procedure}",
            f"post_action: {current_case.post_action}",
            f"is_core_case: {current_case.is_core_case}",
            f"start_mode: {current_case.start_state.mode}",
            f"start_page_id: {current_case.start_state.page_id}",
            f"max_steps: {budget.max_steps}",
            f"max_seconds: {budget.max_seconds}",
            "",
            "[INSTRUCTIONS]",
            "Return a rewritten full draft for this case.",
            "Keep the same business target and verification intent.",
            "If a field should stay unchanged, return the current value rather than generic filler.",
            "You may rewrite post_action when the user prompt asks for cleanup or follow-up changes.",
        ]
        return "\n".join(prompt_lines)


class CaseRewriteService:
    def __init__(
        self,
        *,
        workspace_root: Path,
        plan_store: PlanStore | None = None,
        app_registry: AppRegistry | None = None,
        resolved_config: ResolvedConfig | None = None,
        model: object | None = None,
        agent: CaseRewriteAgent | None = None,
    ) -> None:
        self._workspace_root = workspace_root
        self._plan_store = plan_store or PlanStore()
        self._app_registry = app_registry or AppRegistry(self._plan_store.root_dir)
        self._resolved_config = resolved_config
        self._model = model
        self._agent = agent

    def rewrite_case_preview(self, *, app_id: str, plan_id: str, case_id: str, prompt: str) -> TestCase:
        cleaned_prompt = prompt.strip()
        if not cleaned_prompt:
            raise ValueError("prompt must not be empty")
        plan = self._plan_store.load(app_id, plan_id)
        current_case = next((item for item in plan.cases if item.case_id == case_id), None)
        if current_case is None:
            raise LookupError(f"case '{case_id}' not found in plan '{app_id}/{plan_id}'")
        app_profile, app_introduction = self._load_app_context(app_id)
        draft = self._resolve_agent().rewrite_case(
            app_profile=app_profile,
            app_introduction=app_introduction,
            current_case=current_case,
            user_prompt=cleaned_prompt,
        )
        rewritten = self._merge_draft(current_case=current_case, draft=draft)
        validate_case_for_runner(rewritten)
        return rewritten

    def _load_app_context(self, app_id: str) -> tuple[AppProfile | None, str | None]:
        try:
            app_profile = self._app_registry.load(app_id)
        except FileNotFoundError:
            return None, None
        try:
            app_introduction = self._app_registry.load_introduction(
                app_id,
                ref=app_profile.app_introduction_ref,
            )
        except FileNotFoundError:
            app_introduction = None
        return app_profile, app_introduction

    def _resolve_agent(self) -> CaseRewriteAgent:
        if self._agent is not None:
            return self._agent
        resolved_config = self._resolved_config or load_config_context(None, workspace_root=self._workspace_root)
        if resolved_config is None:
            raise RuntimeError("case rewrite requires a configured LLM, but no config file was found")
        resolved_model = self._resolve_model_config(resolved_config)
        model = self._model or build_pydantic_ai_model(resolved_model, config=resolved_config.config)
        self._agent = PydanticAiCaseRewriteAgent(
            model=model,
            output_strategy=resolve_output_strategy(resolved_model),
        )
        return self._agent

    @staticmethod
    def _resolve_model_config(resolved_config: ResolvedConfig) -> Any:
        resolved = (
            resolve_role_model_config(resolved_config.config, role="plan")
            or resolve_role_model_config(resolved_config.config, role="analysis")
            or resolve_role_model_config(resolved_config.config, role="review")
            or resolve_role_model_config(resolved_config.config, role="judge")
            or resolve_role_model_config(resolved_config.config, role="runner")
        )
        if resolved is None:
            raise RuntimeError("case rewrite requires at least one configured model role")
        return resolved

    @staticmethod
    def _merge_draft(*, current_case: TestCase, draft: CaseRewriteDraft) -> TestCase:
        current_budget = current_case.budget or CaseBudget()
        max_steps = draft.max_steps if draft.max_steps is not None else current_budget.max_steps
        max_seconds = draft.max_seconds if draft.max_seconds is not None else current_budget.max_seconds
        budget = None
        if max_steps is not None or max_seconds is not None:
            budget = CaseBudget(max_steps=max_steps, max_seconds=max_seconds)
        start_mode = cast(Literal["reset", "resume"], draft.start_mode or current_case.start_state.mode)
        start_page_id = draft.start_page_id if draft.start_page_id is not None else current_case.start_state.page_id
        return TestCase(
            case_id=current_case.case_id,
            title=draft.title,
            intent=draft.intent,
            preconditions=list(draft.preconditions if draft.preconditions is not None else current_case.preconditions),
            expected=list(draft.expected if draft.expected is not None else current_case.expected),
            procedure=list(draft.procedure if draft.procedure is not None else current_case.procedure),
            post_action=list(draft.post_action if draft.post_action is not None else current_case.post_action),
            is_core_case=draft.is_core_case if draft.is_core_case is not None else current_case.is_core_case,
            runner_goal=draft.runner_goal,
            budget=budget,
            start_state=CaseStartState(mode=start_mode, page_id=start_page_id),
            source_metadata=dict(current_case.source_metadata),
        )
