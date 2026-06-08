from __future__ import annotations

from typing import Any, cast

from munk.agent_base.llm import run_agent_sync_compatible
from munk.agent_base.output_strategy import append_system_prompt_suffix, build_structured_output_spec
from munk.shared_tools import KnowledgeToolProvider
from pydantic_ai import Agent

from munk.config.schema import OutputStrategy
from munk_runner_local.brain.context_prep_models import ContextPrepFallbackSelectionOutput, ContextPrepOutput
from munk_runner_local.brain.context_prep_tools import ContextPrepDeps, register_context_prep_tools

CONTEXT_PREP_SYSTEM_PROMPT = "\n".join(
    [
        "You prepare app knowledge context for a runner agent.",
        "Read the app introduction, case brief, and seeded knowledge card catalog.",
        "Select only the 1-3 most relevant knowledge cards for the case.",
        "Visible card titles do not prove the business page or flow is already active.",
        "Use the get_knowledge_card_bundle tool exactly once after you decide the relevant card_ids.",
        "Build a concise prep summary that tells the runner what page, flow, assertion, or issue context matters most and what false positives to avoid.",
        "Do not invent card_id or summary details that are absent from knowledge.",
        "If app knowledge is unavailable or not relevant, return a fallback output with empty selections and a non-empty fallback_reason.",
    ]
)

FALLBACK_PREP_SUMMARY = "No prepared app knowledge bundle is available; rely on visible UI evidence and fallback knowledge tools."
CONTEXT_PREP_FALLBACK_SYSTEM_PROMPT = "\n".join(
    [
        "You are the fallback selector for runner app knowledge context.",
        "The primary context prep path failed, so you must work only from the app introduction, case brief, failure reason, and the full knowledge card catalog.",
        "Select only the 1-3 most relevant existing knowledge cards for the case.",
        "Do not invent card_ids that are absent from the provided catalog.",
        "Build a concise prep summary that helps the runner understand what page it should try to reach and how to avoid obvious false positives.",
        "If the catalog is insufficient or you cannot determine relevant cards, return a fallback output with empty selections and a non-empty fallback_reason.",
    ]
)


class ContextPrepAgent:
    def __init__(
        self,
        *,
        model: Any,
        output_strategy: OutputStrategy = "auto",
        max_tokens: int,
        temperature: float,
        top_p: float,
    ) -> None:
        self._model = cast(Any, model)
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._top_p = top_p
        output_spec = build_structured_output_spec(ContextPrepOutput, output_strategy=output_strategy)
        self._agent = Agent[ContextPrepDeps, ContextPrepOutput](
            model=self._model,
            deps_type=ContextPrepDeps,
            output_type=output_spec.output_type,
            system_prompt=append_system_prompt_suffix(
                CONTEXT_PREP_SYSTEM_PROMPT,
                output_spec.system_prompt_suffix,
            ),
            name="context_prep_agent",
            model_settings={"temperature": temperature, "max_tokens": max_tokens, "top_p": top_p},
        )
        register_context_prep_tools(self._agent)
        fallback_output_spec = build_structured_output_spec(
            ContextPrepFallbackSelectionOutput,
            output_strategy="prompted",
        )
        self._fallback_agent = Agent[None, ContextPrepFallbackSelectionOutput](
            model=self._model,
            output_type=fallback_output_spec.output_type,
            system_prompt=append_system_prompt_suffix(
                CONTEXT_PREP_FALLBACK_SYSTEM_PROMPT,
                fallback_output_spec.system_prompt_suffix,
            ),
            name="context_prep_fallback_agent",
            model_settings={"temperature": temperature, "max_tokens": max_tokens, "top_p": top_p},
        )

    def prepare(
        self,
        *,
        app_introduction: str | None,
        case_brief: str,
        knowledge_tools: KnowledgeToolProvider,
    ) -> ContextPrepOutput:
        if not knowledge_tools.list(limit=1):
            return build_context_prep_fallback("app knowledge unavailable")
        prompt = build_context_prep_prompt(
            app_introduction=app_introduction,
            case_brief=case_brief,
            knowledge_card_catalog_text=build_knowledge_card_catalog_text(knowledge_tools),
        )
        result = run_agent_sync_compatible(
            self._agent,
            prompt,
            deps=ContextPrepDeps(knowledge_tools=knowledge_tools),
        )
        return result.output

    def prepare_with_fallback(
        self,
        *,
        app_introduction: str | None,
        case_brief: str,
        knowledge_tools: KnowledgeToolProvider,
    ) -> ContextPrepOutput:
        if not knowledge_tools.list(limit=1):
            return build_context_prep_fallback("app knowledge unavailable")
        try:
            return self.prepare(
                app_introduction=app_introduction,
                case_brief=case_brief,
                knowledge_tools=knowledge_tools,
            )
        except Exception as exc:  # noqa: BLE001
            fallback_selection = self.prepare_fallback_selection(
                app_introduction=app_introduction,
                case_brief=case_brief,
                knowledge_tools=knowledge_tools,
                failure_reason=f"context prep primary failed: {exc}",
            )
            return ContextPrepOutput(
                selected_entries=fallback_selection.selected_entries,
                prep_summary=fallback_selection.prep_summary,
                fallback_reason=fallback_selection.fallback_reason,
            )

    def prepare_fallback_selection(
        self,
        *,
        app_introduction: str | None,
        case_brief: str,
        knowledge_tools: KnowledgeToolProvider,
        failure_reason: str,
    ) -> ContextPrepFallbackSelectionOutput:
        prompt = build_context_prep_fallback_prompt(
            app_introduction=app_introduction,
            case_brief=case_brief,
            knowledge_card_catalog_text=build_knowledge_card_catalog_text(knowledge_tools),
            failure_reason=failure_reason,
        )
        result = run_agent_sync_compatible(self._fallback_agent, prompt)
        return result.output


def build_context_prep_prompt(
    *,
    app_introduction: str | None,
    case_brief: str,
    knowledge_card_catalog_text: str,
) -> str:
    introduction = app_introduction.strip() if app_introduction and app_introduction.strip() else "none"
    return "\n\n".join(
        [
            "[APP_INTRODUCTION]",
            introduction,
            "",
            "[CASE_BRIEF]",
            case_brief.strip(),
            "",
            "[KNOWLEDGE_CARD_CATALOG]",
            knowledge_card_catalog_text.strip() or "none",
        ]
    )


def build_context_prep_fallback(reason: str) -> ContextPrepOutput:
    cleaned_reason = reason.strip() or "context prep unavailable"
    return ContextPrepOutput(
        selected_entries=[],
        prep_summary=FALLBACK_PREP_SUMMARY,
        fallback_reason=cleaned_reason,
    )


def build_context_prep_fallback_prompt(
    *,
    app_introduction: str | None,
    case_brief: str,
    knowledge_card_catalog_text: str,
    failure_reason: str,
) -> str:
    introduction = app_introduction.strip() if app_introduction and app_introduction.strip() else "none"
    return "\n\n".join(
        [
            "[PRIMARY_FAILURE_REASON]",
            failure_reason.strip() or "context prep primary failed",
            "",
            "[APP_INTRODUCTION]",
            introduction,
            "",
            "[CASE_BRIEF]",
            case_brief.strip(),
            "",
            "[KNOWLEDGE_CARD_CATALOG]",
            knowledge_card_catalog_text.strip() or "none",
        ]
    )


def build_knowledge_card_catalog_text(knowledge_tools: KnowledgeToolProvider) -> str:
    cards = knowledge_tools.list(limit=20)
    if not cards:
        return "none"
    return "\n".join(f"- {card.card_id} | {card.card_type} | {card.title}" for card in cards)
