from __future__ import annotations

from typing import Any

from munk.agent_base.llm import build_transcript_http_client
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.openai import OpenAIProvider

from munk.network.proxy import resolve_proxy_config


def build_review_model(*, resolved_config: Any) -> object:
    config = getattr(resolved_config, "config", None)
    if config is None:
        raise ValueError("resolved_config must provide a config object")

    provider = _resolve_role_value(config=config, role="review", attr_name="provider")
    if provider == "openai_compatible":
        section = _resolve_role_section(config=config, role="review", section_name="openai_compatible")
        if section is None:
            raise ValueError("config must include an openai_compatible section for review")
        return _build_openai_model(section, config=config)
    if provider == "gemini":
        section = _resolve_role_section(config=config, role="review", section_name="gemini")
        if section is None:
            raise ValueError("config must include a gemini section for review")
        return _build_gemini_model(section, config=config)
    raise ValueError(f"unsupported model provider: {provider}")


def _build_openai_model(section: Any, *, config: Any) -> object:
    headers = dict(getattr(section, "extra_headers", {}) or {})
    http_client = build_transcript_http_client(
        provider="openai_compatible",
        model=getattr(section, "model"),
        base_url=getattr(section, "base_url"),
        timeout=getattr(section, "timeout_sec", 60.0),
        headers=headers or None,
        proxy=resolve_proxy_config(config),
    )
    provider = OpenAIProvider(
        base_url=getattr(section, "base_url"),
        api_key=getattr(section, "api_key", None) or "unused",
        http_client=http_client,
    )
    from pydantic_ai.models.openai import OpenAIChatModel

    return OpenAIChatModel(getattr(section, "model"), provider=provider)


def _build_gemini_model(section: Any, *, config: Any) -> object:
    http_client = build_transcript_http_client(
        provider="gemini",
        model=getattr(section, "model"),
        base_url=getattr(section, "base_url", None) or "https://generativelanguage.googleapis.com",
        timeout=getattr(section, "timeout_sec", 60.0),
        headers=None,
        proxy=resolve_proxy_config(config),
    )
    provider = GoogleProvider(
        **{
            "api_key": getattr(section, "api_key", None),
            "project": getattr(section, "project", None),
            "location": getattr(section, "location", None),
            "vertexai": getattr(section, "vertexai", False),
            "http_client": http_client,
            "base_url": getattr(section, "base_url", None),
        }
    )
    return GoogleModel(getattr(section, "model"), provider=provider)


def _resolve_role_section(*, config: Any, role: str, section_name: str) -> Any:
    value = _resolve_role_value(config=config, role=role, attr_name=section_name)
    if value is not None:
        return value
    return None


def _resolve_role_value(*, config: Any, role: str, attr_name: str) -> Any:
    agents = getattr(config, "agents", None)
    role_config = getattr(agents, role, None) if agents is not None else None
    value = getattr(role_config, attr_name, None) if role_config is not None else None
    if value is not None:
        return value
    return getattr(config, attr_name, None)
