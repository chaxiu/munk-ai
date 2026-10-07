from __future__ import annotations

from dataclasses import dataclass

from munk.shared_tools import KnowledgeToolProvider
from pydantic_ai import Agent
from pydantic_ai import RunContext as PydanticRunContext

from munk.services.knowledge import render_knowledge_card_summary
from munk_runner_local.brain.context_prep_models import (
    ContextPrepBundleToolArgs,
    ContextPrepBundleToolResult,
    ContextPrepKnowledgeItem,
)


@dataclass(frozen=True)
class ContextPrepDeps:
    knowledge_tools: KnowledgeToolProvider
    recall_candidate_card_ids: tuple[str, ...] = ()


def get_knowledge_card_bundle_payload(
    *,
    knowledge_tools: KnowledgeToolProvider,
    card_ids: list[str],
    recall_candidate_card_ids: tuple[str, ...] = (),
) -> ContextPrepBundleToolResult:
    args = ContextPrepBundleToolArgs(card_ids=card_ids)
    allowed_recall_ids = set(recall_candidate_card_ids)
    items: list[ContextPrepKnowledgeItem] = []
    missing_card_ids: list[str] = []
    for card_id in args.card_ids:
        if allowed_recall_ids and card_id not in allowed_recall_ids:
            missing_card_ids.append(card_id)
            continue
        card = knowledge_tools.get(card_id)
        if card is None:
            missing_card_ids.append(card_id)
            continue
        items.append(
            ContextPrepKnowledgeItem(
                card_id=card.card_id,
                title=card.title,
                card_type=card.card_type,
                summary_text=render_knowledge_card_summary(card),
            )
        )
    return ContextPrepBundleToolResult(items=items, missing_card_ids=missing_card_ids)


def register_context_prep_tools(
    agent: Agent[ContextPrepDeps, object],
) -> None:
    @agent.tool
    def get_knowledge_card_bundle(
        ctx: PydanticRunContext[ContextPrepDeps],
        card_ids: list[str],
    ) -> ContextPrepBundleToolResult:
        """Read 1-3 selected knowledge cards from the recalled candidate list and return compact summaries."""
        return get_knowledge_card_bundle_payload(
            knowledge_tools=ctx.deps.knowledge_tools,
            card_ids=card_ids,
            recall_candidate_card_ids=ctx.deps.recall_candidate_card_ids,
        )
