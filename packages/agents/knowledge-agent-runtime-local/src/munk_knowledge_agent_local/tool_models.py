from __future__ import annotations

import json
from dataclasses import dataclass, field

from munk.knowledge_agent import KnowledgeAgentRequest
from munk.shared_tools.case_run_evidence import (
    build_artifact_manifest_payload,
    build_attempt_summary_payload,
    build_attempts_overview_payload,
    build_decision_trace_tail_payload,
    build_event_history_tail_payload,
    build_retry_handoffs_payload,
)


@dataclass
class KnowledgeToolDeps:
    request: KnowledgeAgentRequest
    tool_budget: int = 6
    tool_calls: list[str] = field(default_factory=list)

    def consume_tool_budget(self, tool_name: str) -> bool:
        if self.tool_budget <= 0:
            return False
        self.tool_budget -= 1
        self.tool_calls.append(tool_name)
        return True

    def tool_budget_exhausted_message(self) -> str:
        return "tool budget exhausted; make the best knowledge candidate judgment from the current context"

    def structured_evidence(self) -> dict[str, object]:
        evidence = self.request.structured_evidence
        return dict(evidence) if isinstance(evidence, dict) else {}

    def artifact_ids(self) -> list[str]:
        ids = [artifact.artifact_id for artifact in self.request.evidence_bundle.artifacts]
        if self.request.evidence_bundle.judge_result_path is not None and "judge_result" not in ids:
            ids.append("judge_result")
        return sorted(set(ids))

    def read_judge_result(self) -> str:
        payload = self.structured_evidence().get("judge_result")
        if isinstance(payload, dict):
            return json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return json.dumps(
            self.request.evidence_bundle.judge_result.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
        )

    def read_attempts_overview(self) -> str:
        return build_attempts_overview_payload(self.structured_evidence().get("attempts"))

    def read_attempt_summary(self, attempt_index: int) -> str:
        return build_attempt_summary_payload(self.structured_evidence().get("attempts"), attempt_index)

    def read_retry_handoffs(self) -> str:
        return build_retry_handoffs_payload(self.structured_evidence().get("retry_handoffs"))

    def read_event_history_tail(self, last_n: int) -> str:
        evidence = self.structured_evidence()
        return build_event_history_tail_payload(
            evidence.get("history"),
            last_n=last_n,
            fallback=evidence.get("runner_history"),
        )

    def read_decision_trace_tail(self, last_n: int) -> str:
        return build_decision_trace_tail_payload(
            self.structured_evidence().get("decision_trace"),
            last_n=last_n,
        )

    def read_artifact_manifest(self) -> str:
        return build_artifact_manifest_payload(
            self.structured_evidence().get("artifact_manifest"),
            available_artifacts=self.artifact_ids(),
        )
