from __future__ import annotations

from munk.shared_tools import KnowledgeToolProvider

from .guidance import KNOWLEDGE_RECALL_SECTION_TITLE
from .recall import (
    DEFAULT_PLAN_KNOWLEDGE_RECALL_LIMIT,
    KnowledgeRecallResult,
    build_knowledge_recall,
    build_plan_case_recall_query,
    build_plan_change_recall_query,
    build_plan_skeleton_recall_query,
)


def build_plan_knowledge_recall_section(
    provider: KnowledgeToolProvider,
    *,
    query_text: str,
    app_introduction: str,
    limit: int = DEFAULT_PLAN_KNOWLEDGE_RECALL_LIMIT,
) -> tuple[str, KnowledgeRecallResult]:
    recall = build_knowledge_recall(
        provider,
        query_text=query_text,
        app_introduction=app_introduction,
        limit=limit,
    )
    return f"{KNOWLEDGE_RECALL_SECTION_TITLE}:\n{recall.candidates_text}", recall


__all__ = [
    "build_knowledge_recall",
    "build_plan_case_recall_query",
    "build_plan_change_recall_query",
    "build_plan_knowledge_recall_section",
    "build_plan_skeleton_recall_query",
]
