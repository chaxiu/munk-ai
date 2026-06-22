from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from pydantic import BaseModel

from munk.token_usage import TokenUsage, merge_token_usages, token_usage_has_values

from .transcript_models import LlmResponseTranscriptEntry, parse_llm_transcript_entry


def summarize_llm_transcript_usage(path: Path | None) -> TokenUsage | None:
    if path is None or not path.exists() or not path.is_file():
        return None
    usages: list[TokenUsage] = []
    with path.open("r", encoding="utf-8") as file_handle:
        for line in file_handle:
            raw = line.strip()
            if not raw:
                continue
            try:
                entry = parse_llm_transcript_entry(json.loads(raw))
            except json.JSONDecodeError:
                continue
            usage = extract_usage_from_transcript_entry(entry)
            if usage is not None:
                usages.append(usage)
    return merge_token_usages(usages)


def extract_response_token_usage(
    body: object,
    *,
    provider: str | None,
    model: str | None,
) -> TokenUsage | None:
    usage_map = find_usage_map(body)
    if usage_map is None:
        return None
    usage = TokenUsage(
        input_tokens=get_usage_int(usage_map, "input_tokens", "prompt_tokens", "promptTokenCount"),
        output_tokens=get_usage_int(usage_map, "output_tokens", "completion_tokens", "candidatesTokenCount"),
        total_tokens=get_usage_int(usage_map, "total_tokens", "totalTokenCount"),
        cached_input_tokens=get_usage_int(
            usage_map,
            "cached_input_tokens",
            "cached_tokens",
            "cachedContentTokenCount",
            "prompt_tokens_details.cached_tokens",
        ),
        reasoning_tokens=get_usage_int(
            usage_map,
            "reasoning_tokens",
            "reasoning_token_count",
            "thoughtsTokenCount",
            "completion_tokens_details.reasoning_tokens",
        ),
        request_count=1,
        provider=provider,
        model=model,
    )
    if not token_usage_has_values(usage):
        return None
    return usage


def extract_usage_from_transcript_entry(entry: object) -> TokenUsage | None:
    normalized = entry if isinstance(entry, BaseModel) else parse_llm_transcript_entry(entry)
    if not isinstance(normalized, LlmResponseTranscriptEntry):
        return None
    if normalized.token_usage is not None and token_usage_has_values(normalized.token_usage):
        return normalized.token_usage
    return extract_response_token_usage(
        normalized.body,
        provider=normalized.provider or None,
        model=normalized.model or None,
    )


def find_usage_map(body: object) -> dict[str, object] | None:
    if not isinstance(body, Mapping):
        return None
    for key in ("usage", "usage_metadata", "usageMetadata"):
        candidate = body.get(key)
        if isinstance(candidate, Mapping):
            return {str(name): value for name, value in candidate.items()}
    return None


def get_usage_int(container: Mapping[str, object], *paths: str) -> int | None:
    for path in paths:
        value = lookup_usage_path(container, path)
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                continue
    return None


def lookup_usage_path(container: Mapping[str, object], path: str) -> object:
    current: object = container
    for segment in path.split("."):
        if not isinstance(current, Mapping):
            return None
        current = current.get(segment)
    return current
