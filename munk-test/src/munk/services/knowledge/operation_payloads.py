from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from munk.services.knowledge.request_models import KnowledgePostActionResult


class KnowledgePostActionOperationResultPayload(BaseModel):
    summary: str
    submitted: bool = False
    skip_reason: str | None = None
    candidate_id: str | None = None
    knowledge_post_action_result_path: str
    knowledge_post_action_request_path: str
    knowledge_post_action_diagnostics_path: str
    knowledge_post_action_tool_calls_path: str
    artifacts: dict[str, str]

    def to_command_data(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"artifacts"})


def build_knowledge_post_action_operation_result_payload(
    result: KnowledgePostActionResult,
    *,
    tool_calls_path: str,
) -> KnowledgePostActionOperationResultPayload:
    return KnowledgePostActionOperationResultPayload(
        summary=result.summary,
        submitted=result.submitted,
        skip_reason=result.skip_reason,
        candidate_id=result.candidate_id,
        knowledge_post_action_result_path=str(result.result_path),
        knowledge_post_action_request_path=str(result.request_path),
        knowledge_post_action_diagnostics_path=str(result.diagnostics_path),
        knowledge_post_action_tool_calls_path=tool_calls_path,
        artifacts=dict(result.artifacts),
    )
