from __future__ import annotations

from types import SimpleNamespace

import pytest
from munk.knowledge_agent.errors import (
    KnowledgeAgentRuntimeConflictError,
    KnowledgeAgentRuntimeUnavailableError,
)
from munk.knowledge_agent.health import KnowledgeAgentRuntimeHealth
from munk.knowledge_agent.runtime import diagnose_knowledge_agent_runtime, resolve_knowledge_agent_runtime_factory


class FakeEntryPoint:
    def __init__(self, name: str, factory) -> None:  # noqa: ANN001
        self.name = name
        self._factory = factory

    def load(self):  # noqa: ANN201
        return self._factory


class FakeFactory:
    runtime_id = "local"

    def create_runtime(self, *, resolved_config):  # noqa: ANN001, ANN201
        return SimpleNamespace(resolved_config=resolved_config)

    def diagnose(self) -> KnowledgeAgentRuntimeHealth:
        return KnowledgeAgentRuntimeHealth(runtime_id="local", status="ok", message="available")


def test_resolve_knowledge_agent_runtime_factory_requires_installed_runtime(monkeypatch) -> None:
    monkeypatch.setattr("munk.knowledge_agent.runtime.entry_points", lambda group: [])
    with pytest.raises(KnowledgeAgentRuntimeUnavailableError):
        resolve_knowledge_agent_runtime_factory()


def test_resolve_knowledge_agent_runtime_factory_detects_conflict(monkeypatch) -> None:
    monkeypatch.setattr(
        "munk.knowledge_agent.runtime.entry_points",
        lambda group: [
            FakeEntryPoint("local", FakeFactory),
            FakeEntryPoint("remote", FakeFactory),
        ],
    )
    with pytest.raises(KnowledgeAgentRuntimeConflictError):
        resolve_knowledge_agent_runtime_factory()


def test_diagnose_knowledge_agent_runtime_uses_selected_factory(monkeypatch) -> None:
    monkeypatch.setattr(
        "munk.knowledge_agent.runtime.entry_points",
        lambda group: [FakeEntryPoint("local", FakeFactory)],
    )
    health = diagnose_knowledge_agent_runtime()
    assert health.runtime_id == "local"
    assert health.status == "ok"
