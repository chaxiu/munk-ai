from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Callable, cast

from munk.app_knowledge import KnowledgeCandidateRecord, KnowledgeCandidateSubmission, KnowledgeCard
from munk.shared_tools.knowledge import (
    build_knowledge_get_payload,
    build_knowledge_list_payload,
    build_knowledge_search_payload,
    parse_knowledge_card_type,
    parse_knowledge_card_types,
    register_knowledge_tools,
)
from pydantic import TypeAdapter
from pydantic_ai import Agent

KnowledgeCardAdapter = TypeAdapter(KnowledgeCard)


def _screen_card() -> KnowledgeCard:
    return KnowledgeCardAdapter.validate_python(
        {
            "card_id": "screen-home",
            "app_id": "app-1",
            "title": "首页",
            "card_type": "screen",
            "status": "active",
            "confidence": 0.9,
            "updated_at": "2026-06-06T00:00:00Z",
            "source": {"kind": "import", "ref": "app_knowledge.json"},
            "payload": {
                "enter": "点击首页 tab",
                "recognize": "看到首页主内容流",
                "key_elements": ["首页 tab"],
                "exit_signals": ["进入详情页"],
            },
        }
    )


@dataclass(frozen=True)
class _Provider:
    expected_app_id: str = "app-1"
    last_search_card_types: object | None = None

    def search(self, query: str, *, card_types=None, limit: int = 8) -> list[KnowledgeCard]:  # noqa: ANN001
        object.__setattr__(self, "last_search_card_types", card_types)
        return [_screen_card()]

    def get(self, card_id: str) -> KnowledgeCard | None:
        return _screen_card() if card_id == "screen-home" else None

    def list(self, *, card_type=None, limit: int = 20) -> list[KnowledgeCard]:  # noqa: ANN001
        return [_screen_card()]

    def submit_candidate(self, submission: KnowledgeCandidateSubmission) -> KnowledgeCandidateRecord:
        return KnowledgeCandidateRecord.model_validate(
            {
                "candidate_id": "candidate-1",
                "app_id": submission.app_id,
                "status": "pending_review",
                "submitted_at": "2026-06-06T00:00:00Z",
                "candidate": submission.candidate.model_dump(mode="python"),
                "evidence_refs": submission.evidence_refs,
            }
        )


def test_parse_knowledge_card_types_keeps_valid_and_discards_invalid() -> None:
    parsed = parse_knowledge_card_types("screen,Foo,FLOW,screen")
    assert parsed.filter_types == ["screen", "flow"]
    assert parsed.ignored == ("Foo",)
    assert parse_knowledge_card_types(None).filter_types is None
    assert parse_knowledge_card_types("").filter_types is None
    assert parse_knowledge_card_types("Nope,Bad").filter_types is None
    assert parse_knowledge_card_type("Screen") == "screen"
    assert parse_knowledge_card_type("Nope") is None


def test_build_knowledge_search_payload_contains_summary() -> None:
    payload = build_knowledge_search_payload(app_id="app-1", query="首页", items=[_screen_card()])
    assert '"count": 1' in payload
    assert '"query": "首页"' in payload
    assert '"card_id": "screen-home"' in payload


def test_build_knowledge_search_payload_includes_ignored_types_when_present() -> None:
    payload = build_knowledge_search_payload(
        app_id="app-1",
        query="首页",
        items=[_screen_card()],
        ignored_card_types=["Foo"],
    )
    assert '"ignored_card_types": ["Foo"]' in payload


def test_build_knowledge_get_payload_contains_full_card() -> None:
    payload = build_knowledge_get_payload(card_id="screen-home", card=_screen_card())
    assert '"found": true' in payload
    assert '"card_type": "screen"' in payload
    assert '"payload"' in payload


def test_build_knowledge_list_payload_contains_summary() -> None:
    payload = build_knowledge_list_payload(app_id="app-1", card_type="screen", items=[_screen_card()])
    assert '"card_type": "screen"' in payload
    assert '"count": 1' in payload


def test_register_knowledge_tools_returns_stable_payloads() -> None:
    agent: Agent[object, str] = Agent(model="test", output_type=str, defer_model_check=True)
    register_knowledge_tools(agent, provider_getter=lambda deps: deps.provider)
    tools = agent._function_toolset.tools
    deps = SimpleNamespace(provider=_Provider())

    search_tool = cast(Callable[..., str], tools["knowledge_search"].function)
    get_tool = cast(Callable[..., str], tools["knowledge_get"].function)
    list_tool = cast(Callable[..., str], tools["knowledge_list"].function)

    search_payload = search_tool(SimpleNamespace(deps=deps), query="首页")
    get_payload = get_tool(SimpleNamespace(deps=deps), card_id="screen-home")
    list_payload = list_tool(SimpleNamespace(deps=deps), card_type="screen")

    assert '"card_id": "screen-home"' in search_payload
    assert '"found": true' in get_payload
    assert '"card_type": "screen"' in list_payload
    assert "app_id" not in tools["knowledge_search"].function_schema.json_schema["properties"]
    assert "app_id" not in tools["knowledge_list"].function_schema.json_schema["properties"]
    assert tools["knowledge_search"].function_schema.json_schema["properties"]["card_types"]["anyOf"][0][
        "type"
    ] == "string"


def test_register_knowledge_tools_discards_invalid_card_types() -> None:
    agent: Agent[object, str] = Agent(model="test", output_type=str, defer_model_check=True)
    register_knowledge_tools(agent, provider_getter=lambda deps: deps.provider)
    tools = agent._function_toolset.tools
    provider = _Provider()
    deps = SimpleNamespace(provider=provider)
    search_tool = cast(Callable[..., str], tools["knowledge_search"].function)

    payload = search_tool(
        SimpleNamespace(deps=deps),
        query="首页",
        card_types="screen,Foo,FLOW",
    )

    assert provider.last_search_card_types == ["screen", "flow"]
    assert '"ignored_card_types": ["Foo"]' in payload


def test_register_knowledge_tools_can_skip_submit_candidate() -> None:
    agent: Agent[object, str] = Agent(model="test", output_type=str, defer_model_check=True)
    register_knowledge_tools(
        agent,
        provider_getter=lambda deps: deps.provider,
        include_submit_candidate=False,
    )

    assert set(agent._function_toolset.tools) == {"knowledge_search", "knowledge_get", "knowledge_list"}
