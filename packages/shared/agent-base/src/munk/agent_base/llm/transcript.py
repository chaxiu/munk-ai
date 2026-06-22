from __future__ import annotations

from typing import Mapping
from uuid import uuid4

import httpx

from munk.network.proxy import ResolvedProxyConfig, build_httpx_proxy_kwargs

from .transcript_models import (
    ENV_LLM_TRANSCRIPT,
    LlmRequestTranscriptEntry,
    LlmResponseTranscriptEntry,
    LlmTranscriptEntry,
    llm_transcript_observer_scope,
    llm_transcript_scope,
    parse_llm_transcript_entry,
)
from .transcript_payloads import (
    decode_http_body,
    normalize_openai_chat_request_body,
    redact_headers,
    rewrite_json_request_content,
)
from .transcript_store import (
    append_llm_request_entry,
    append_llm_response_entry,
    prepare_llm_transcript_path,
    should_capture_llm_transcript,
)
from .transcript_text import extract_transcript_entry_text
from .transcript_usage import extract_response_token_usage, summarize_llm_transcript_usage


def build_transcript_http_client(
    *,
    provider: str,
    model: str,
    base_url: str,
    timeout: float,
    headers: Mapping[str, str] | None,
    thinking: bool | None = None,
    proxy: ResolvedProxyConfig | None = None,
) -> httpx.AsyncClient:
    base_headers = dict(headers or {})

    async def on_request(request: httpx.Request) -> None:
        request_id = uuid4().hex
        request.extensions["munk_llm_request_id"] = request_id
        decoded_body = decode_http_body(request.content)
        normalized_body = normalize_openai_chat_request_body(
            decoded_body,
            request=request,
            thinking=thinking,
        )
        if normalized_body is not decoded_body:
            rewrite_json_request_content(request, normalized_body)
        append_llm_request_entry(
            provider=provider,
            model=model,
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            headers=redact_headers(dict(request.headers)),
            body=normalized_body,
        )

    async def on_response(response: httpx.Response) -> None:
        request = response.request
        request_id = str(request.extensions.get("munk_llm_request_id", ""))
        try:
            await response.aread()
            body: object = decode_http_body(response.content)
        except Exception as exc:  # noqa: BLE001
            body = {"read_error": str(exc)}
        token_usage = extract_response_token_usage(body, provider=provider, model=model)
        append_llm_response_entry(
            provider=provider,
            model=model,
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            headers=redact_headers(dict(response.headers)),
            body=body,
            token_usage=token_usage,
        )

    return httpx.AsyncClient(
        timeout=timeout,
        headers=base_headers or None,
        event_hooks={
            "request": [on_request],
            "response": [on_response],
        },
        **build_httpx_proxy_kwargs(url=base_url, proxy=proxy),
    )


__all__ = [
    "ENV_LLM_TRANSCRIPT",
    "LlmRequestTranscriptEntry",
    "LlmResponseTranscriptEntry",
    "LlmTranscriptEntry",
    "append_llm_request_entry",
    "append_llm_response_entry",
    "build_transcript_http_client",
    "extract_response_token_usage",
    "extract_transcript_entry_text",
    "llm_transcript_observer_scope",
    "llm_transcript_scope",
    "parse_llm_transcript_entry",
    "prepare_llm_transcript_path",
    "should_capture_llm_transcript",
    "summarize_llm_transcript_usage",
]
