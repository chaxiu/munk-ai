from __future__ import annotations

import hashlib
import re

from .models import KnowledgeCard, KnowledgeCardType

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def generate_candidate_card_id(
    *,
    card_type: KnowledgeCardType,
    title: str,
    existing_cards: list[KnowledgeCard],
) -> str:
    base_slug = _slugify(title) or "candidate"
    base_id = f"{card_type}-{base_slug}"
    existing_ids = {card.card_id for card in existing_cards}
    if base_id not in existing_ids:
        return base_id
    suffix = hashlib.sha1(title.strip().encode("utf-8")).hexdigest()[:8]
    candidate = f"{base_id}-{suffix}"
    if candidate not in existing_ids:
        return candidate
    index = 2
    while True:
        candidate = f"{base_id}-{index}"
        if candidate not in existing_ids:
            return candidate
        index += 1


def _slugify(value: str) -> str:
    lowered = value.strip().lower()
    normalized = _NON_ALNUM_RE.sub("-", lowered).strip("-")
    return normalized
