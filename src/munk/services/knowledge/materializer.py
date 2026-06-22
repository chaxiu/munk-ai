from __future__ import annotations

import json
from pathlib import Path

from munk.post_run_analysis import PostRunAnalysisAgentInput


class KnowledgePostActionMaterializer:
    def paths(self, *, run_dir: Path) -> dict[str, Path]:
        root = run_dir / "knowledge"
        root.mkdir(parents=True, exist_ok=True)
        return {
            "root": root,
            "request": root / "knowledge_post_action_request.json",
            "agent_input": root / "knowledge_post_action_agent_input.json",
            "result": root / "knowledge_post_action_result.json",
            "diagnostics": root / "knowledge_post_action_diagnostics.json",
            "tool_calls": root / "knowledge_post_action_tool_calls.json",
            "prompt": root / "knowledge_post_action_prompt.txt",
            "llm_transcript": root / "knowledge_post_action_llm_transcript.json",
        }

    @staticmethod
    def write_agent_input(path: Path, agent_input: PostRunAnalysisAgentInput) -> None:
        path.write_text(agent_input.model_dump_json(indent=2), encoding="utf-8")

    @staticmethod
    def write_diagnostics(path: Path, payload: dict[str, object]) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
