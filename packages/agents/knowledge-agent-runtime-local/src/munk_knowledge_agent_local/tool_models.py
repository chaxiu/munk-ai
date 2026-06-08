from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from munk.knowledge_agent import KnowledgeAgentRequest


def _load_json(path: Path | None) -> object:
    if path is None or not path.exists() or not path.is_file():
        return None
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _load_jsonl(path: Path | None) -> list[object] | None:
    if path is None or not path.exists() or not path.is_file():
        return None
    items: list[object] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            items.append(json.loads(stripped))
        except json.JSONDecodeError:
            continue
    return items


@dataclass
class KnowledgeToolDeps:
    request: KnowledgeAgentRequest
    tool_budget: int = 6
    tool_calls: list[str] = field(default_factory=list)
    _json_cache: dict[str, object | None] = field(default_factory=dict)
    _jsonl_cache: dict[str, list[object] | None] = field(default_factory=dict)

    def artifact_path(self, artifact_id: str) -> Path | None:
        for artifact in self.request.evidence_bundle.artifacts:
            if artifact.artifact_id == artifact_id:
                return artifact.path
        if artifact_id == "judge_result":
            return self.request.evidence_bundle.judge_result_path
        return None

    def artifact_ids(self) -> list[str]:
        ids = [artifact.artifact_id for artifact in self.request.evidence_bundle.artifacts]
        if self.request.evidence_bundle.judge_result_path is not None and "judge_result" not in ids:
            ids.append("judge_result")
        return sorted(set(ids))

    def read_json_artifact(self, artifact_id: str) -> object | None:
        if artifact_id not in self._json_cache:
            self._json_cache[artifact_id] = _load_json(self.artifact_path(artifact_id))
        return self._json_cache[artifact_id]

    def read_jsonl_artifact(self, artifact_id: str) -> list[object] | None:
        if artifact_id not in self._jsonl_cache:
            self._jsonl_cache[artifact_id] = _load_jsonl(self.artifact_path(artifact_id))
        return self._jsonl_cache[artifact_id]
