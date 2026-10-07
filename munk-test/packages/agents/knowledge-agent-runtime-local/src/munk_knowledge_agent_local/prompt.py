from __future__ import annotations

import json

from munk.knowledge_agent.models import KnowledgeAgentRequest
from munk.shared_tools.prompt_seed import (
    build_post_run_prompt_seed,
    build_prompt_size_diagnostics,
    maybe_degrade_prompt_seed,
)
from pydantic_ai.messages import TextContent, UserContent

SYSTEM_PROMPT = "\n".join(
    [
        "You are a knowledge agent for mobile UI automation runs.",
        "Your job is to convert credible run evidence into reusable knowledge candidates for later human approval.",
        "Prefer stable failure patterns, trigger conditions, and workarounds over verbose execution retellings.",
        "Start from the compact evidence_seed. Use the read tools when that minimal context is insufficient.",
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
    evidence_seed = build_post_run_prompt_seed(
        request.structured_evidence if isinstance(request.structured_evidence, dict) else {},
        include_tails=True,
    )
    evidence_seed, degraded = maybe_degrade_prompt_seed(evidence_seed)
    payload = {
        "case": {
            "app_id": request.app_id,
            "plan_id": request.plan_id,
            "case_id": request.case_id,
            "case_title": request.case_title,
            "run_dir": str(request.run_dir),
        },
        "evidence_seed": evidence_seed,
        "available_artifacts": [
            {"artifact_id": artifact.artifact_id, "path": str(artifact.path)}
            for artifact in request.evidence_bundle.artifacts
        ],
        "requirements": {
            "output_kind": "knowledge_candidate_submissions",
            "prefer_zero_or_few_candidates": True,
            "must_be_reviewable": True,
            "must_be_grounded_in_run_evidence": True,
            "use_read_tools_for_detail": True,
        },
    }
    if degraded:
        payload["prompt_degraded"] = True
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def build_knowledge_agent_prompt_diagnostics(prompt_text: str) -> dict[str, object]:
    degraded = False
    try:
        payload = json.loads(prompt_text)
    except json.JSONDecodeError:
        payload = {}
    if isinstance(payload, dict):
        degraded = bool(payload.get("prompt_degraded"))
        seed = payload.get("evidence_seed")
        if isinstance(seed, dict) and seed.get("degraded"):
            degraded = True
    return build_prompt_size_diagnostics(prompt_text, degraded=degraded)
