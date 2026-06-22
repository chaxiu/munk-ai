from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from munk.app_knowledge import KnowledgeCard, KnowledgeCardType
from munk.shared_tools import KnowledgeToolProvider

DEFAULT_KNOWLEDGE_RECALL_LIMIT = 10
DEFAULT_PLAN_KNOWLEDGE_RECALL_LIMIT = 12
DEFAULT_SMALL_CATALOG_THRESHOLD = 15
NAVIGATION_CARD_TYPES: tuple[KnowledgeCardType, ...] = ("screen", "flow")

# Backward-compatible aliases for context prep callers.
DEFAULT_CONTEXT_PREP_RECALL_LIMIT = DEFAULT_KNOWLEDGE_RECALL_LIMIT


@dataclass(frozen=True)
class KnowledgeRecallResult:
    mode: Literal["full_catalog", "search"]
    query: str | None
    candidate_count: int
    candidate_card_ids: tuple[str, ...]
    candidates_text: str


ContextPrepRecallResult = KnowledgeRecallResult


def build_knowledge_recall_query(*, query_text: str, app_introduction: str | None) -> str:
    parts: list[str] = []
    cleaned_query = query_text.strip()
    if cleaned_query:
        parts.append(cleaned_query)
    if app_introduction and app_introduction.strip():
        intro = app_introduction.strip()
        if len(intro) > 200:
            intro = intro[:200].rstrip() + "..."
        parts.append(intro)
    return "\n".join(parts)


def build_context_prep_recall_query(*, case_brief: str, app_introduction: str | None) -> str:
    return build_knowledge_recall_query(query_text=case_brief, app_introduction=app_introduction)


def format_knowledge_recall_candidates_text(cards: Sequence[KnowledgeCard]) -> str:
    if not cards:
        return "none"
    return "\n".join(f"- {card.card_id} | {card.card_type} | {card.title}" for card in cards)


def build_knowledge_recall(
    provider: KnowledgeToolProvider,
    *,
    query_text: str,
    app_introduction: str | None = None,
    limit: int = DEFAULT_KNOWLEDGE_RECALL_LIMIT,
    small_catalog_threshold: int = DEFAULT_SMALL_CATALOG_THRESHOLD,
    include_navigation_boost: bool = True,
) -> KnowledgeRecallResult:
    catalog_probe = provider.list(limit=small_catalog_threshold + 1)
    if not catalog_probe:
        return KnowledgeRecallResult(
            mode="full_catalog",
            query=None,
            candidate_count=0,
            candidate_card_ids=(),
            candidates_text="none",
        )
    if len(catalog_probe) <= small_catalog_threshold:
        return _build_recall_result(mode="full_catalog", query=None, cards=catalog_probe)

    query = build_knowledge_recall_query(query_text=query_text, app_introduction=app_introduction)
    if not query.strip():
        return _build_recall_result(mode="full_catalog", query=None, cards=catalog_probe[:limit])

    primary = provider.search(query, limit=limit)
    merged = list(primary)
    if include_navigation_boost:
        navigation = provider.search(query, card_types=list(NAVIGATION_CARD_TYPES), limit=4)
        merged = _merge_knowledge_cards(primary, navigation)
    cards = merged[:limit]
    if not cards:
        return _build_recall_result(mode="full_catalog", query=query, cards=catalog_probe[:limit])
    return _build_recall_result(mode="search", query=query, cards=cards)


def build_context_prep_recall(
    provider: KnowledgeToolProvider,
    *,
    case_brief: str,
    app_introduction: str | None,
    limit: int = DEFAULT_CONTEXT_PREP_RECALL_LIMIT,
    small_catalog_threshold: int = DEFAULT_SMALL_CATALOG_THRESHOLD,
) -> KnowledgeRecallResult:
    return build_knowledge_recall(
        provider,
        query_text=case_brief,
        app_introduction=app_introduction,
        limit=limit,
        small_catalog_threshold=small_catalog_threshold,
    )


def build_plan_skeleton_recall_query(*, requirement_doc: str) -> str:
    return requirement_doc.strip()


def build_plan_change_recall_query(
    *,
    acceptance_criteria: list[str],
    change_summary: str,
    diff_text: str,
    requirement_doc: str | None,
) -> str:
    parts: list[str] = []
    if acceptance_criteria:
        ac_text = "\n".join(f"- {criterion}" for criterion in acceptance_criteria)
        parts.append(ac_text[:2000])
    if change_summary.strip():
        parts.append(change_summary.strip())
    trimmed_diff = diff_text.strip()
    if trimmed_diff:
        parts.append(trimmed_diff[:2000])
    if requirement_doc and requirement_doc.strip():
        parts.append(requirement_doc.strip()[:1500])
    return "\n".join(part for part in parts if part)


def build_plan_case_recall_query(
    *,
    skeleton_name: str,
    skeleton_summary: str,
    requirement_section: str,
    case_index: int,
    coverage_summary: str,
) -> str:
    parts = [
        f"Plan: {skeleton_name.strip()}",
        skeleton_summary.strip(),
        requirement_section.strip(),
        f"Generate case number {case_index + 1}",
    ]
    if coverage_summary.strip() and coverage_summary.strip() != "none generated yet":
        parts.append(f"Existing coverage:\n{coverage_summary.strip()}")
    return "\n".join(part for part in parts if part)


def _build_recall_result(
    *,
    mode: Literal["full_catalog", "search"],
    query: str | None,
    cards: Sequence[KnowledgeCard],
) -> KnowledgeRecallResult:
    card_ids = tuple(card.card_id for card in cards)
    return KnowledgeRecallResult(
        mode=mode,
        query=query,
        candidate_count=len(cards),
        candidate_card_ids=card_ids,
        candidates_text=format_knowledge_recall_candidates_text(cards),
    )


def _merge_knowledge_cards(*groups: Sequence[KnowledgeCard]) -> list[KnowledgeCard]:
    seen: set[str] = set()
    merged: list[KnowledgeCard] = []
    for group in groups:
        for card in group:
            if card.card_id in seen:
                continue
            seen.add(card.card_id)
            merged.append(card)
    return merged
