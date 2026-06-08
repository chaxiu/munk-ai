from __future__ import annotations

import json

from munk.knowledge_agent.models import KnowledgeAgentRequest
from pydantic_ai.messages import TextContent, UserContent

SYSTEM_PROMPT = "\n".join(
    [
        "You are a knowledge agent for mobile UI automation runs.",
        "Your job is to convert credible run evidence into reusable knowledge candidates for later human approval.",
        "Prefer stable failure patterns, trigger conditions, and workarounds over verbose execution retellings.",
        "Use the read tools when the minimal context is insufficient.",
        "Only generate candidates when the evidence is strong enough to survive review.",
        "For passed cases, prefer returning no candidate unless the prompt context explicitly proves a reusable knowledge gap.",
        "Keep candidate titles compact and durable.",
        "Use evidence_refs that point to the most relevant artifact paths already available in the request context.",
        "Return only the structured output.",
    ]
)


def build_knowledge_agent_user_prompt(request: KnowledgeAgentRequest) -> list[UserContent]:
    payload_text = build_knowledge_agent_prompt_payload(request)
    return [TextContent(content=payload_text)]


def build_knowledge_agent_prompt_payload(request: KnowledgeAgentRequest) -> str:
    payload = {
        "case": {
            "app_id": request.app_id,
            "plan_id": request.plan_id,
            "case_id": request.case_id,
            "case_title": request.case_title,
            "run_dir": str(request.run_dir),
        },
        "judge_result_summary": request.evidence_bundle.judge_result.model_dump(mode="json"),
        "available_artifacts": [
            {"artifact_id": artifact.artifact_id, "path": str(artifact.path)}
            for artifact in request.evidence_bundle.artifacts
        ],
        "requirements": {
            "output_kind": "knowledge_candidate_submissions",
            "prefer_zero_or_few_candidates": True,
            "must_be_reviewable": True,
            "must_be_grounded_in_run_evidence": True,
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
