from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic_ai import Agent
from pydantic_ai import RunContext as PydanticRunContext

APP_KNOWLEDGE_LIST_KEYS_TOOL = "list_app_knowledge_keys"
APP_KNOWLEDGE_GET_ENTRY_TOOL = "get_app_knowledge_entry"
APP_KNOWLEDGE_SEARCH_TOOL = "search_app_knowledge"
DEFAULT_MAX_SEED_KEYS = 40
DEFAULT_MAX_SEARCH_RESULTS = 8


@dataclass(frozen=True)
class AppKnowledgeToolEntry:
    key: str
    enter: str | None = None
    recognize: str | None = None

    def tool_payload(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "enter": self.enter,
            "recognize": self.recognize,
        }


class AppKnowledgeToolProvider(Protocol):
    expected_app_id: str

    def list_keys(self) -> list[str]: ...

    def get_entry(self, key: str) -> AppKnowledgeToolEntry | None: ...

    def search(self, query: str, *, limit: int = DEFAULT_MAX_SEARCH_RESULTS) -> list[AppKnowledgeToolEntry]: ...


@dataclass(frozen=True)
class AppKnowledgeToolDeps:
    provider: AppKnowledgeToolProvider


@dataclass(frozen=True)
class AppKnowledgeToolDescriptions:
    list_keys: str = ""
    get_entry: str = ""
    search: str = ""


def build_app_knowledge_keys_text(
    keys: Sequence[str],
    *,
    max_seed_keys: int = DEFAULT_MAX_SEED_KEYS,
) -> str:
    if not keys:
        return "none"
    lines = [f"- total keys: {len(keys)}"]
    lines.extend(f"- {key}" for key in list(keys)[:max_seed_keys])
    if len(keys) > max_seed_keys:
        lines.append("- ...")
    return "\n".join(lines)


def build_app_knowledge_list_payload(*, app_id: str, keys: Sequence[str]) -> str:
    return _json_payload(
        {
            "app_id": app_id,
            "count": len(keys),
            "keys": list(keys),
        }
    )


def build_app_knowledge_entry_payload(
    *,
    app_id: str,
    key: str,
    entry: AppKnowledgeToolEntry | None,
) -> str:
    if entry is None:
        return _json_payload(
            {
                "app_id": app_id,
                "found": False,
                "key": key.strip() or key,
                "enter": None,
                "recognize": None,
            }
        )
    return _json_payload(
        {
            "app_id": app_id,
            "found": True,
            **entry.tool_payload(),
        }
    )


def build_app_knowledge_search_payload(
    *,
    app_id: str,
    query: str,
    items: Sequence[AppKnowledgeToolEntry],
) -> str:
    return _json_payload(
        {
            "app_id": app_id,
            "query": query.strip(),
            "count": len(items),
            "items": [item.tool_payload() for item in items],
        }
    )


def build_app_knowledge_mismatch_payload(*, expected_app_id: str, received_app_id: str) -> str:
    return _json_payload(
        {
            "app_id": expected_app_id,
            "error": f"app_id mismatch: expected {expected_app_id}, got {received_app_id}",
        }
    )


def app_knowledge_app_id_matches(*, expected_app_id: str, received_app_id: str) -> bool:
    return expected_app_id == received_app_id


def register_app_knowledge_tools(
    agent: Agent[Any, Any],
    *,
    provider_getter: Callable[[Any], AppKnowledgeToolProvider],
    recorder: Callable[[str, dict[str, object], str], str] | None = None,
    descriptions: AppKnowledgeToolDescriptions | None = None,
) -> None:
    descriptions = descriptions or AppKnowledgeToolDescriptions()

    def _maybe_record(tool_name: str, arguments: dict[str, object], payload: str) -> str:
        if recorder is None:
            return payload
        return recorder(tool_name, arguments, payload)

    @agent.tool
    def list_app_knowledge_keys(ctx: PydanticRunContext[Any], app_id: str) -> str:
        """Read the available app knowledge keys for the current app."""
        provider = provider_getter(ctx.deps)
        arguments: dict[str, object] = {"app_id": app_id}
        if not app_knowledge_app_id_matches(expected_app_id=provider.expected_app_id, received_app_id=app_id):
            payload = build_app_knowledge_mismatch_payload(
                expected_app_id=provider.expected_app_id,
                received_app_id=app_id,
            )
            return _maybe_record(APP_KNOWLEDGE_LIST_KEYS_TOOL, arguments, payload)
        payload = build_app_knowledge_list_payload(app_id=provider.expected_app_id, keys=provider.list_keys())
        return _maybe_record(APP_KNOWLEDGE_LIST_KEYS_TOOL, arguments, payload)

    @agent.tool
    def get_app_knowledge_entry(ctx: PydanticRunContext[Any], app_id: str, key: str) -> str:
        """Read one app knowledge entry by key."""
        provider = provider_getter(ctx.deps)
        arguments: dict[str, object] = {"app_id": app_id, "key": key}
        if not app_knowledge_app_id_matches(expected_app_id=provider.expected_app_id, received_app_id=app_id):
            payload = build_app_knowledge_mismatch_payload(
                expected_app_id=provider.expected_app_id,
                received_app_id=app_id,
            )
            return _maybe_record(APP_KNOWLEDGE_GET_ENTRY_TOOL, arguments, payload)
        payload = build_app_knowledge_entry_payload(
            app_id=provider.expected_app_id,
            key=key,
            entry=provider.get_entry(key),
        )
        return _maybe_record(APP_KNOWLEDGE_GET_ENTRY_TOOL, arguments, payload)

    @agent.tool
    def search_app_knowledge(ctx: PydanticRunContext[Any], app_id: str, query: str) -> str:
        """Search app knowledge by business flow or page text."""
        provider = provider_getter(ctx.deps)
        arguments: dict[str, object] = {"app_id": app_id, "query": query}
        if not app_knowledge_app_id_matches(expected_app_id=provider.expected_app_id, received_app_id=app_id):
            payload = build_app_knowledge_mismatch_payload(
                expected_app_id=provider.expected_app_id,
                received_app_id=app_id,
            )
            return _maybe_record(APP_KNOWLEDGE_SEARCH_TOOL, arguments, payload)
        payload = build_app_knowledge_search_payload(
            app_id=provider.expected_app_id,
            query=query,
            items=provider.search(query),
        )
        return _maybe_record(APP_KNOWLEDGE_SEARCH_TOOL, arguments, payload)


def _json_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)
