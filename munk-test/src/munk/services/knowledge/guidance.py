from __future__ import annotations

KNOWLEDGE_RECALL_SECTION_TITLE = "Knowledge Recall Candidates"

PLAN_KNOWLEDGE_GUIDANCE_LINES: tuple[str, ...] = (
    "- Start from the pre-recalled knowledge candidates in the prompt; they are ranked by hybrid retrieval (keyword + semantic).",
    "- Use knowledge_search or knowledge_get when candidates are insufficient or you need full card payload details.",
    "- Prefer screen and flow cards for navigation understanding, but use assertion, issue, policy, or data cards when they materially improve plan quality.",
    "- Do not invent knowledge card details when the candidate list is empty or inconclusive.",
)

PLAN_CHANGE_KNOWLEDGE_GUIDANCE_LINES: tuple[str, ...] = (
    "- Start from the pre-recalled knowledge candidates in the prompt; they are ranked by hybrid retrieval (keyword + semantic).",
    "- Use knowledge_search or knowledge_get when candidates are insufficient or you need full card payload details.",
    "- Prefer screen and flow cards for changed navigation coverage, but pull assertion or issue cards when they better describe the regression risk.",
    "- Do not invent knowledge card details when the candidate list is empty or inconclusive.",
)

RUNNER_PREPARED_KNOWLEDGE_GUIDANCE_LINES: tuple[str, ...] = (
    "Treat the prepared context summary as the primary app knowledge hint for this run.",
    "The summary was distilled from hybrid-recalled candidates before the run started.",
    "If the summary is absent or inconclusive, use knowledge_search or knowledge_get before inventing page assertions or flow constraints.",
)
