from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import AppKnowledgeImportDocument, KnowledgeCard, KnowledgeCardType

DEFAULT_SEARCH_LIMIT = 8
DEFAULT_LIST_LIMIT = 20


def flatten_knowledge_card_text(card: KnowledgeCard) -> str:
    parts = [card.card_id, card.title, card.card_type]
    if card.source.ref:
        parts.append(card.source.ref)
    if card.source.note:
        parts.append(card.source.note)
    parts.extend(_flatten_json(card.payload.model_dump(mode="json")))
    return "\n".join(part for part in parts if part).lower()


def render_knowledge_card_summary(card: KnowledgeCard) -> str:
    lines = [
        f"- card_id: {card.card_id}",
        f"  title: {card.title}",
        f"  card_type: {card.card_type}",
        f"  status: {card.status}",
    ]
    payload = card.payload.model_dump(mode="json")
    summary_lines = _render_payload_summary(payload)
    if summary_lines:
        lines.extend(f"  {line}" for line in summary_lines[:6])
    return "\n".join(lines)


@dataclass(frozen=True)
class ImportedKnowledgeRepository:
    document: AppKnowledgeImportDocument

    @property
    def app_id(self) -> str:
        return self.document.app_id

    def list_cards(
        self,
        app_id: str,
        *,
        card_type: KnowledgeCardType | None = None,
        limit: int = DEFAULT_LIST_LIMIT,
    ) -> list[KnowledgeCard]:
        if app_id.strip() != self.app_id or limit <= 0:
            return []
        items = self._filtered_cards(card_type=card_type)
        return items[:limit]

    def get_card(self, card_id: str) -> KnowledgeCard | None:
        normalized_card_id = card_id.strip()
        if not normalized_card_id:
            return None
        for card in self.document.cards:
            if card.card_id == normalized_card_id:
                return card
        return None

    def search_cards(
        self,
        app_id: str,
        query: str,
        *,
        card_types: list[KnowledgeCardType] | None = None,
        limit: int = DEFAULT_SEARCH_LIMIT,
    ) -> list[KnowledgeCard]:
        normalized_app_id = app_id.strip()
        normalized_query = query.strip().lower()
        if normalized_app_id != self.app_id or not normalized_query or limit <= 0:
            return []
        matched_types = {card_type for card_type in (card_types or [])}
        ranked: list[tuple[int, KnowledgeCard]] = []
        for position, card in enumerate(self.document.cards):
            if matched_types and card.card_type not in matched_types:
                continue
            score = _score_card_match(card, normalized_query)
            if score <= 0:
                continue
            ranked.append((score * 10_000 - position, card))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [card for _score, card in ranked[:limit]]

    def _filtered_cards(self, *, card_type: KnowledgeCardType | None) -> list[KnowledgeCard]:
        if card_type is None:
            return list(self.document.cards)
        return [card for card in self.document.cards if card.card_type == card_type]


def _score_card_match(card: KnowledgeCard, query: str) -> int:
    if card.card_id.lower() == query:
        return 5
    if card.title.lower() == query:
        return 4
    if query in card.card_id.lower():
        return 4
    if query in card.title.lower():
        return 3
    if query in flatten_knowledge_card_text(card):
        return 2
    return 0


def _flatten_json(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    if isinstance(value, (bool, int, float)):
        return [str(value)]
    if isinstance(value, list):
        list_parts: list[str] = []
        for item in value:
            list_parts.extend(_flatten_json(item))
        return list_parts
    if isinstance(value, dict):
        dict_parts: list[str] = []
        for key, item in value.items():
            dict_parts.append(str(key))
            dict_parts.extend(_flatten_json(item))
        return dict_parts
    return [str(value)]


def _render_payload_summary(payload: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key, value in payload.items():
        fragments = _flatten_json(value)
        if not fragments:
            continue
        summary = "; ".join(fragments[:4])
        lines.append(f"{key}: {summary}")
    return lines
