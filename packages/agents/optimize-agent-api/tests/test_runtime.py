from __future__ import annotations

from types import SimpleNamespace

import pytest
from munk.optimizing.errors import OptimizeRuntimeConflictError, OptimizeRuntimeUnavailableError
from munk.optimizing.health import OptimizeRuntimeHealth
from munk.optimizing.runtime import diagnose_optimize_runtime, resolve_optimize_runtime_factory


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

    def diagnose(self) -> OptimizeRuntimeHealth:
        return OptimizeRuntimeHealth(runtime_id="local", status="ok", message="available")


def test_resolve_optimize_runtime_factory_requires_installed_runtime(monkeypatch) -> None:
    monkeypatch.setattr("munk.optimizing.runtime.entry_points", lambda group: [])
    with pytest.raises(OptimizeRuntimeUnavailableError):
        resolve_optimize_runtime_factory()


def test_resolve_optimize_runtime_factory_detects_conflict(monkeypatch) -> None:
    monkeypatch.setattr(
        "munk.optimizing.runtime.entry_points",
        lambda group: [
            FakeEntryPoint("local", FakeFactory),
            FakeEntryPoint("remote", FakeFactory),
        ],
    )
    with pytest.raises(OptimizeRuntimeConflictError):
        resolve_optimize_runtime_factory()


def test_diagnose_optimize_runtime_uses_selected_factory(monkeypatch) -> None:
    monkeypatch.setattr(
        "munk.optimizing.runtime.entry_points",
        lambda group: [FakeEntryPoint("local", FakeFactory)],
    )
    health = diagnose_optimize_runtime()
    assert health.runtime_id == "local"
    assert health.status == "ok"
