from __future__ import annotations

from collections.abc import Iterable

from pydantic import BaseModel


class TokenUsage(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    cached_input_tokens: int | None = None
    reasoning_tokens: int | None = None
    request_count: int = 0
    provider: str | None = None
    model: str | None = None


def token_usage_has_values(usage: TokenUsage | None) -> bool:
    if usage is None:
        return False
    return any(
        value is not None
        for value in (
            usage.input_tokens,
            usage.output_tokens,
            usage.total_tokens,
            usage.cached_input_tokens,
            usage.reasoning_tokens,
        )
    ) or usage.request_count > 0


def merge_token_usages(
    usages: Iterable[TokenUsage | None],
    *,
    provider: str | None = None,
    model: str | None = None,
) -> TokenUsage | None:
    merged = TokenUsage(provider=provider, model=model)
    providers: set[str] = set()
    models: set[str] = set()
    seen = False
    for usage in usages:
        if usage is None or not token_usage_has_values(usage):
            continue
        seen = True
        merged.input_tokens = _sum_optional(merged.input_tokens, usage.input_tokens)
        merged.output_tokens = _sum_optional(merged.output_tokens, usage.output_tokens)
        merged.total_tokens = _sum_optional(merged.total_tokens, usage.total_tokens)
        merged.cached_input_tokens = _sum_optional(merged.cached_input_tokens, usage.cached_input_tokens)
        merged.reasoning_tokens = _sum_optional(merged.reasoning_tokens, usage.reasoning_tokens)
        merged.request_count += usage.request_count
        if usage.provider:
            providers.add(usage.provider)
        if usage.model:
            models.add(usage.model)
    if not seen:
        return None
    if provider is None and len(providers) == 1:
        merged.provider = next(iter(providers))
    if model is None and len(models) == 1:
        merged.model = next(iter(models))
    return merged


def _sum_optional(current: int | None, incoming: int | None) -> int | None:
    if incoming is None:
        return current
    if current is None:
        return incoming
    return current + incoming
