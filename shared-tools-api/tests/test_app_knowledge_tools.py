from __future__ import annotations

from dataclasses import dataclass

from munk.shared_tools.app_knowledge import (
    AppKnowledgeToolEntry,
    build_app_knowledge_entry_payload,
    build_app_knowledge_keys_text,
    build_app_knowledge_list_payload,
    build_app_knowledge_search_payload,
)


@dataclass(frozen=True)
class _Entry:
    key: str
    enter: str | None = None
    recognize: str | None = None


def test_build_keys_text_lists_keys() -> None:
    payload = build_app_knowledge_keys_text(["首页", "设置"])
    assert "- total keys: 2" in payload
    assert "- 首页" in payload
    assert "- 设置" in payload


def test_build_list_payload_contains_keys() -> None:
    payload = build_app_knowledge_list_payload(app_id="app-1", keys=["首页"])
    assert '"app_id": "app-1"' in payload
    assert '"count": 1' in payload


def test_build_entry_payload_handles_missing_entry() -> None:
    payload = build_app_knowledge_entry_payload(app_id="app-1", key="不存在", entry=None)
    assert '"found": false' in payload
    assert '"key": "不存在"' in payload


def test_build_search_payload_contains_items() -> None:
    payload = build_app_knowledge_search_payload(
        app_id="app-1",
        query="设置",
        items=[AppKnowledgeToolEntry(key="设置", enter="进入设置", recognize="看到设置页")],
    )
    assert '"count": 1' in payload
    assert '"query": "设置"' in payload
