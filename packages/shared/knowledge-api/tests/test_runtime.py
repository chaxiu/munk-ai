from __future__ import annotations

from pathlib import Path

from munk.knowledge import KnowledgeManagedPaths, KnowledgeRuntimeContext, KnowledgeRuntimeHealth


def test_runtime_health_accepts_generic_status_and_details() -> None:
    health = KnowledgeRuntimeHealth(
        runtime_id="infra",
        status="warning",
        message="generic contract only",
        details={"phase": "split"},
    )

    assert health.runtime_id == "infra"
    assert health.details["phase"] == "split"


def test_runtime_context_carries_generic_managed_paths() -> None:
    context = KnowledgeRuntimeContext(
        operation_id="op-1",
        managed_paths=KnowledgeManagedPaths(root_dir=Path(".")),
    )

    assert context.operation_id == "op-1"
    assert context.managed_paths.root_dir == Path(".")
