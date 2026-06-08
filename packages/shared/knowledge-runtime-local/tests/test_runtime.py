from __future__ import annotations

import json
from pathlib import Path

from munk.app_knowledge import (
    KnowledgeCandidateSubmission,
    KnowledgeGetRequest,
    KnowledgeListRequest,
    KnowledgeSearchRequest,
    KnowledgeSubmitCandidateRequest,
    build_knowledge_runtime_factory,
)
from munk.knowledge import KnowledgeManagedPaths, KnowledgeRuntimeContext
from munk_knowledge_local import default_app_knowledge_model_dir

from munk.app_assets.storage import AppRegistry


def test_build_knowledge_runtime_factory_creates_runtime() -> None:
    factory = build_knowledge_runtime_factory()
    runtime = factory.create_runtime(resolved_config={"model": "dummy"})

    assert factory.runtime_id == "local"
    assert runtime.runtime_id == "local"


def test_shared_embedding_model_is_bundled() -> None:
    assert default_app_knowledge_model_dir().exists()


def test_local_runtime_diagnose_reports_ok() -> None:
    factory = build_knowledge_runtime_factory()
    health = factory.diagnose()

    assert health.runtime_id == "local"
    assert health.status == "ok"
    assert health.details["implementation"] == "local_build_backed"


def test_local_runtime_search_get_list_and_submit_candidate(tmp_path: Path) -> None:
    registry = AppRegistry(root_dir=tmp_path)
    registry.save_knowledge(
        "app-1",
        json.dumps(
            {
                "schema_version": "knowledge.import.v1",
                "app_id": "app-1",
                "cards": [
                    {
                        "card_id": "screen-login",
                        "app_id": "app-1",
                        "title": "登录页",
                        "card_type": "screen",
                        "status": "active",
                        "confidence": 0.95,
                        "updated_at": "2026-06-06T00:00:00Z",
                        "source": {"kind": "import", "ref": "app_knowledge.json"},
                        "payload": {
                            "enter": "打开 app 后看到登录页",
                            "recognize": "看到手机号输入框和登录按钮",
                            "key_elements": ["手机号输入框"],
                            "exit_signals": ["进入首页"],
                        },
                    }
                ],
            },
            ensure_ascii=False,
        ),
    )
    factory = build_knowledge_runtime_factory()
    runtime = factory.create_runtime(resolved_config={"app_registry_root": tmp_path})
    context = KnowledgeRuntimeContext(
        operation_id=None,
        managed_paths=KnowledgeManagedPaths(root_dir=tmp_path),
    )

    search_output = runtime.search(
        KnowledgeSearchRequest(app_id="app-1", query="登录", limit=5),
        context=context,
    )
    list_output = runtime.list(
        KnowledgeListRequest(app_id="app-1", card_type="screen", limit=5),
        context=context,
    )
    get_output = runtime.get(KnowledgeGetRequest(card_id="screen-login"), context=context)
    submit_output = runtime.submit_candidate(
        KnowledgeSubmitCandidateRequest(
            submission=KnowledgeCandidateSubmission.model_validate(
                {
                    "app_id": "app-1",
                    "candidate": {
                        "app_id": "app-1",
                        "title": "登录失败问题",
                        "confidence": 0.8,
                        "source": {"kind": "knowledge_agent", "note": "judge post action"},
                        "card_type": "issue",
                        "payload": {
                            "symptoms": ["点击登录后没有进入首页"],
                            "trigger_conditions": ["case_id=case-1"],
                            "severity": "high",
                        },
                    },
                    "evidence_refs": [str(tmp_path / "judge_result.json")],
                }
            )
        ),
        context=context,
    )

    assert search_output.total_count == 1
    assert list_output.items[0].card_id == "screen-login"
    assert get_output.card is not None
    assert get_output.card.title == "登录页"
    assert submit_output.candidate is not None
    assert submit_output.candidate.status == "pending_review"
    assert (tmp_path / "apps" / "app-1" / "knowledge_candidates.json").exists()
    assert (tmp_path / "apps" / "app-1" / "knowledge_build" / "app_knowledge.sqlite").exists()
    assert (tmp_path / "apps" / "app-1" / "knowledge_build" / "build_manifest.json").exists()


def test_local_runtime_rebuilds_when_source_changes(tmp_path: Path) -> None:
    registry = AppRegistry(root_dir=tmp_path)
    registry.save_knowledge(
        "app-1",
        json.dumps(
            {
                "schema_version": "knowledge.import.v1",
                "app_id": "app-1",
                "cards": [
                    {
                        "card_id": "screen-login",
                        "app_id": "app-1",
                        "title": "旧登录页",
                        "card_type": "screen",
                        "status": "active",
                        "confidence": 0.95,
                        "updated_at": "2026-06-06T00:00:00Z",
                        "source": {"kind": "import", "ref": "app_knowledge.json"},
                        "payload": {
                            "enter": "打开 app 后看到旧登录页",
                            "recognize": "旧登录按钮",
                            "key_elements": ["旧按钮"],
                            "exit_signals": ["进入首页"],
                        },
                    }
                ],
            },
            ensure_ascii=False,
        ),
    )
    runtime = build_knowledge_runtime_factory().create_runtime(resolved_config={"app_registry_root": tmp_path})
    context = KnowledgeRuntimeContext(
        operation_id=None,
        managed_paths=KnowledgeManagedPaths(root_dir=tmp_path),
    )

    first = runtime.search(KnowledgeSearchRequest(app_id="app-1", query="旧登录页", limit=5), context=context)
    registry.save_knowledge(
        "app-1",
        json.dumps(
            {
                "schema_version": "knowledge.import.v1",
                "app_id": "app-1",
                "cards": [
                    {
                        "card_id": "screen-login",
                        "app_id": "app-1",
                        "title": "新登录页",
                        "card_type": "screen",
                        "status": "active",
                        "confidence": 0.95,
                        "updated_at": "2026-06-07T00:00:00Z",
                        "source": {"kind": "import", "ref": "app_knowledge.json"},
                        "payload": {
                            "enter": "打开 app 后看到新登录页",
                            "recognize": "新登录按钮",
                            "key_elements": ["新按钮"],
                            "exit_signals": ["进入首页"],
                        },
                    }
                ],
            },
            ensure_ascii=False,
        ),
    )

    second = runtime.search(KnowledgeSearchRequest(app_id="app-1", query="新登录页", limit=5), context=context)

    assert first.items[0].title == "旧登录页"
    assert second.items[0].title == "新登录页"
