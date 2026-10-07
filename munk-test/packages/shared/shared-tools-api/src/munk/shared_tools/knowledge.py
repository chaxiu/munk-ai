from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, get_args

from munk.app_knowledge import (
    KnowledgeCandidateDraft,
    KnowledgeCandidateRecord,
    KnowledgeCandidateSubmission,
    KnowledgeCard,
    KnowledgeCardType,
)
from pydantic_ai import Agent
from pydantic_ai import RunContext as PydanticRunContext

KNOWLEDGE_SEARCH_TOOL = "knowledge_search"
KNOWLEDGE_GET_TOOL = "knowledge_get"
KNOWLEDGE_LIST_TOOL = "knowledge_list"
KNOWLEDGE_SUBMIT_CANDIDATE_TOOL = "knowledge_submit_candidate"
DEFAULT_MAX_SEARCH_RESULTS = 8
DEFAULT_MAX_LIST_RESULTS = 20
KNOWLEDGE_CARD_TYPE_VALUES: frozenset[str] = frozenset(get_args(KnowledgeCardType))
KNOWLEDGE_CARD_TYPES_HINT = ",".join(sorted(KNOWLEDGE_CARD_TYPE_VALUES))


class KnowledgeToolProvider(Protocol):
    expected_app_id: str

    def search(
        self,
        query: str,
        *,
        card_types: Sequence[KnowledgeCardType] | None = None,
        limit: int = DEFAULT_MAX_SEARCH_RESULTS,
    ) -> list[KnowledgeCard]: ...

    def get(self, card_id: str) -> KnowledgeCard | None: ...

    def list(
        self,
        *,
        card_type: KnowledgeCardType | None = None,
        limit: int = DEFAULT_MAX_LIST_RESULTS,
    ) -> list[KnowledgeCard]: ...

    def submit_candidate(self, submission: KnowledgeCandidateSubmission) -> KnowledgeCandidateRecord: ...


@dataclass(frozen=True)
class KnowledgeToolDescriptions:
    search: str = ""
    get: str = ""
    list: str = ""
    submit_candidate: str = ""


@dataclass(frozen=True)
class ParsedKnowledgeCardTypes:
    """Accepted enum values after discarding unknown tokens."""

    accepted: tuple[KnowledgeCardType, ...]
    ignored: tuple[str, ...]

    @property
    def filter_types(self) -> list[KnowledgeCardType] | None:
        if not self.accepted:
            return None
        return list(self.accepted)


def parse_knowledge_card_types(raw: str | None) -> ParsedKnowledgeCardTypes:
    """Parse comma-separated card types; keep only known enum values.

    Invalid tokens are discarded (not raised). When nothing valid remains,
    the filter is treated as absent (search all types).
    """
    if raw is None:
        return ParsedKnowledgeCardTypes(accepted=(), ignored=())
    text = raw.strip()
    if not text:
        return ParsedKnowledgeCardTypes(accepted=(), ignored=())

    accepted: list[KnowledgeCardType] = []
    ignored: list[str] = []
    seen: set[str] = set()
    for part in text.split(","):
        token = part.strip()
        if not token:
            continue
        normalized = token.lower()
        if normalized in KNOWLEDGE_CARD_TYPE_VALUES:
            if normalized not in seen:
                seen.add(normalized)
                accepted.append(normalized)  # type: ignore[arg-type]
            continue
        ignored.append(token)
    return ParsedKnowledgeCardTypes(accepted=tuple(accepted), ignored=tuple(ignored))


def parse_knowledge_card_type(raw: str | None) -> KnowledgeCardType | None:
    """Parse a single card type; discard invalid values as None."""
    parsed = parse_knowledge_card_types(raw)
    if not parsed.accepted:
        return None
    return parsed.accepted[0]


def build_knowledge_search_payload(
    *,
    app_id: str,
    query: str,
    items: Sequence[KnowledgeCard],
    ignored_card_types: Sequence[str] = (),
) -> str:
    payload: dict[str, Any] = {
        "app_id": app_id,
        "query": query.strip(),
        "count": len(items),
        "items": [_card_summary(item) for item in items],
    }
    if ignored_card_types:
        payload["ignored_card_types"] = list(ignored_card_types)
    return _json_payload(payload)


def build_knowledge_get_payload(*, card_id: str, card: KnowledgeCard | None) -> str:
    if card is None:
        return _json_payload({"card_id": card_id.strip() or card_id, "found": False, "card": None})
    return _json_payload({"card_id": card.card_id, "found": True, "card": card.model_dump(mode="json")})


def build_knowledge_list_payload(
    *,
    app_id: str,
    card_type: KnowledgeCardType | None,
    items: Sequence[KnowledgeCard],
) -> str:
    return _json_payload(
        {
            "app_id": app_id,
            "card_type": card_type,
            "count": len(items),
            "items": [_card_summary(item) for item in items],
        }
    )


def build_knowledge_submit_candidate_payload(
    *,
    app_id: str,
    record: KnowledgeCandidateRecord,
) -> str:
    return _json_payload(
        {
            "app_id": app_id,
            "candidate": record.model_dump(mode="json"),
        }
    )


def build_knowledge_mismatch_payload(*, expected_app_id: str, received_app_id: str) -> str:
    return _json_payload(
        {
            "app_id": expected_app_id,
            "error": f"app_id mismatch: expected {expected_app_id}, got {received_app_id}",
        }
    )


def knowledge_app_id_matches(*, expected_app_id: str, received_app_id: str) -> bool:
    return expected_app_id == received_app_id


def register_knowledge_tools(
    agent: Agent[Any, Any],
    *,
    provider_getter: Callable[[Any], KnowledgeToolProvider],
    recorder: Callable[[Any, str, dict[str, object], str], str] | None = None,
    descriptions: KnowledgeToolDescriptions | None = None,
    include_submit_candidate: bool = True,
) -> None:
    descriptions = descriptions or KnowledgeToolDescriptions()

    def _maybe_record(deps: Any, tool_name: str, arguments: dict[str, object], payload: str) -> str:
        if recorder is None:
            return payload
        return recorder(deps, tool_name, arguments, payload)

    search_description = (
        descriptions.search
        or (
            "Search knowledge cards by natural language query. "
            "Do not pass app_id; the host binds the current app. "
            f"Optional card_types is a comma-separated filter "
            f"(allowed: {KNOWLEDGE_CARD_TYPES_HINT}); omit unless filtering. "
            "Unknown types are ignored."
        )
    )
    list_description = (
        descriptions.list
        or (
            "List knowledge cards for the current app. "
            "Do not pass app_id; the host binds the current app. "
            f"Optional card_type is one of: {KNOWLEDGE_CARD_TYPES_HINT}; "
            "unknown values are ignored."
        )
    )

    @agent.tool(description=search_description)
    def knowledge_search(
        ctx: PydanticRunContext[Any],
        query: str,
        card_types: str | None = None,
        limit: int = DEFAULT_MAX_SEARCH_RESULTS,
    ) -> str:
        """Search knowledge cards by natural language query."""
        provider = provider_getter(ctx.deps)
        parsed = parse_knowledge_card_types(card_types)
        arguments: dict[str, object] = {
            "app_id": provider.expected_app_id,
            "query": query,
            "card_types": card_types,
            "accepted_card_types": list(parsed.accepted),
            "ignored_card_types": list(parsed.ignored),
            "limit": limit,
        }
        payload = build_knowledge_search_payload(
            app_id=provider.expected_app_id,
            query=query,
            items=provider.search(query, card_types=parsed.filter_types, limit=limit),
            ignored_card_types=parsed.ignored,
        )
        return _maybe_record(ctx.deps, KNOWLEDGE_SEARCH_TOOL, arguments, payload)

    @agent.tool
    def knowledge_get(ctx: PydanticRunContext[Any], card_id: str) -> str:
        """Read one full knowledge card by card_id."""
        provider = provider_getter(ctx.deps)
        arguments: dict[str, object] = {"card_id": card_id}
        payload = build_knowledge_get_payload(card_id=card_id, card=provider.get(card_id))
        return _maybe_record(ctx.deps, KNOWLEDGE_GET_TOOL, arguments, payload)

    @agent.tool(description=list_description)
    def knowledge_list(
        ctx: PydanticRunContext[Any],
        card_type: str | None = None,
        limit: int = DEFAULT_MAX_LIST_RESULTS,
    ) -> str:
        """List knowledge cards for the current app."""
        provider = provider_getter(ctx.deps)
        resolved_card_type = parse_knowledge_card_type(card_type)
        arguments: dict[str, object] = {
            "app_id": provider.expected_app_id,
            "card_type": card_type,
            "resolved_card_type": resolved_card_type,
            "limit": limit,
        }
        payload = build_knowledge_list_payload(
            app_id=provider.expected_app_id,
            card_type=resolved_card_type,
            items=provider.list(card_type=resolved_card_type, limit=limit),
        )
        return _maybe_record(ctx.deps, KNOWLEDGE_LIST_TOOL, arguments, payload)

    if include_submit_candidate:

        @agent.tool
        def knowledge_submit_candidate(
            ctx: PydanticRunContext[Any],
            app_id: str,
            candidate: KnowledgeCandidateDraft,
            evidence_refs: list[str] | None = None,
        ) -> str:
            """Submit a knowledge candidate for later review and approval."""
            provider = provider_getter(ctx.deps)
            arguments: dict[str, object] = {
                "app_id": app_id,
                "candidate": candidate.model_dump(mode="json"),
                "evidence_refs": list(evidence_refs or []),
            }
            if not knowledge_app_id_matches(expected_app_id=provider.expected_app_id, received_app_id=app_id):
                payload = build_knowledge_mismatch_payload(
                    expected_app_id=provider.expected_app_id,
                    received_app_id=app_id,
                )
                return _maybe_record(ctx.deps, KNOWLEDGE_SUBMIT_CANDIDATE_TOOL, arguments, payload)
            submission = KnowledgeCandidateSubmission(
                app_id=app_id,
                candidate=candidate,
                evidence_refs=list(evidence_refs or []),
            )
            payload = build_knowledge_submit_candidate_payload(
                app_id=provider.expected_app_id,
                record=provider.submit_candidate(submission),
            )
            return _maybe_record(ctx.deps, KNOWLEDGE_SUBMIT_CANDIDATE_TOOL, arguments, payload)


def _card_summary(card: KnowledgeCard) -> dict[str, Any]:
    return {
        "card_id": card.card_id,
        "app_id": card.app_id,
        "title": card.title,
        "card_type": card.card_type,
        "status": card.status,
        "confidence": card.confidence,
        "updated_at": card.updated_at,
        "source": card.source.model_dump(mode="json"),
    }


def _json_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)
