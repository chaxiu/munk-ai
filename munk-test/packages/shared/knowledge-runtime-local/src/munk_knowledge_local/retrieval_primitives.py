from __future__ import annotations

import re
from typing import Any


def build_fts_query(text: str, *, max_terms: int = 24) -> str:
    trimmed = text.strip().lower()
    if not trimmed:
        return ""
    tokens = [
        token
        for token in re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]{2,16}", trimmed)
        if len(token) >= 2
    ]
    deduped = list(dict.fromkeys(tokens))
    if deduped:
        return " OR ".join(f'"{token}"' for token in deduped[:max_terms])
    return f'"{trimmed[:64]}"'


def merge_ranked_candidates(
    *,
    filter_rows: list[dict[str, Any]],
    fts_rows: list[dict[str, Any]],
    vector_rows: list[dict[str, Any]],
    id_field: str,
    limit: int,
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for row in filter_rows:
        item = merged.setdefault(str(row[id_field]), dict(row))
        item["filter_score"] = float(row.get("filter_score", 0.0))
        item.setdefault("retrieval_channels", []).append("filter")
    for rank, row in enumerate(fts_rows, start=1):
        item = merged.setdefault(str(row[id_field]), dict(row))
        item["fts_score"] = float(row.get("fts_score", 0.0))
        item["fts_rank"] = rank
        item.setdefault("retrieval_channels", []).append("fts")
    for rank, row in enumerate(vector_rows, start=1):
        item = merged.setdefault(str(row[id_field]), dict(row))
        item["vector_distance"] = float(row.get("vector_distance", 0.0))
        item["vector_rank"] = rank
        item.setdefault("retrieval_channels", []).append("vector")

    ranked: list[dict[str, Any]] = []
    for item in merged.values():
        filter_score = float(item.get("filter_score", 0.0))
        fts_rank = int(item.get("fts_rank", 999))
        vector_rank = int(item.get("vector_rank", 999))
        fts_score = 1.0 / (fts_rank + 1) if "fts_rank" in item else 0.0
        vector_score = 1.0 / (vector_rank + 1) if "vector_rank" in item else 0.0
        filter_boost = 0.10 if filter_score > 0 else 0.0
        item["combined_score"] = (fts_score * 0.45) + (vector_score * 0.45) + filter_boost
        item["channel_count"] = len(set(item.get("retrieval_channels", [])))
        ranked.append(item)

    ranked.sort(
        key=lambda item: (
            item.get("combined_score", 0.0),
            item.get("channel_count", 0),
            -int(item.get("fts_rank", 999)),
            -int(item.get("vector_rank", 999)),
        ),
        reverse=True,
    )
    return ranked[:limit]


def build_excerpt(text: str, *, query_text: str = "", max_chars: int = 600) -> str:
    normalized = text.strip()
    if len(normalized) <= max_chars:
        return normalized
    lowered = normalized.lower()
    query = query_text.strip().lower()
    if query:
        for token in re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]{2,16}", query):
            position = lowered.find(token)
            if position >= 0:
                start = max(0, position - int(max_chars * 0.25))
                end = min(len(normalized), start + max_chars)
                return normalized[start:end].strip()
    return normalized[:max_chars].strip()
