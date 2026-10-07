from __future__ import annotations

from types import SimpleNamespace

import pytest
from munk.running.errors import RunnerRuntimeConflictError, RunnerRuntimeUnavailableError
from munk.running.health import RunnerRuntimeHealth
from munk.running.runtime import diagnose_runner_runtime, resolve_runner_runtime_factory


class FakeEntryPoint:
    def __init__(self, name: str, factory) -> None:  # noqa: ANN001
        self.name = name
        self._factory = factory

    def load(self):  # noqa: ANN201
        return self._factory


class FakeFactory:
    runtime_id = "local"

    def create_runtime(self, *, resolved_config, event_sink=None):  # noqa: ANN001, ANN201
        return SimpleNamespace(resolved_config=resolved_config, event_sink=event_sink)

    def diagnose(self) -> RunnerRuntimeHealth:
        return RunnerRuntimeHealth(runtime_id="local", status="ok", message="available")


def test_resolve_runner_runtime_factory_requires_installed_runtime(monkeypatch) -> None:
    monkeypatch.setattr("munk.running.runtime.entry_points", lambda group: [])
    with pytest.raises(RunnerRuntimeUnavailableError):
        resolve_runner_runtime_factory()


def test_resolve_runner_runtime_factory_detects_conflict(monkeypatch) -> None:
    monkeypatch.setattr(
        "munk.running.runtime.entry_points",
        lambda group: [
            FakeEntryPoint("local", FakeFactory),
            FakeEntryPoint("remote", FakeFactory),
        ],
    )
    with pytest.raises(RunnerRuntimeConflictError):
        resolve_runner_runtime_factory()


def test_diagnose_runner_runtime_uses_selected_factory(monkeypatch) -> None:
    monkeypatch.setattr(
        "munk.running.runtime.entry_points",
        lambda group: [FakeEntryPoint("local", FakeFactory)],
    )
    health = diagnose_runner_runtime()
    assert health.runtime_id == "local"
    assert health.status == "ok"
