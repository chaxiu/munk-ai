from __future__ import annotations

from typing import Any, cast

from munk.agent_base.output_strategy import append_system_prompt_suffix, build_structured_output_spec
from pydantic_ai import Agent

from munk.config.schema import OutputStrategy

from .review_agent_models import ReviewResultDraft

SYSTEM_PROMPT = "\n".join(
    [
        "You are a local code review agent.",
        "Review the provided code change using only the supplied change context and retrieved knowledge cards.",
        "Do not claim runtime behavior, test results, or device execution outcomes unless explicitly provided.",
        "Focus on actionable review findings, regression risks, and missing verification.",
        "Every finding must stay grounded in the changed files or retrieved knowledge cards.",
        "When knowledge cards are relevant, cite their case_id values in knowledge_case_ids.",
        "Keep summaries concise and repair-oriented.",
        "Return only the structured result payload.",
        "Do not wrap the result in markdown fences.",
        "Use the exact field names defined below. Do not invent synonyms such as description or checks.",
        "risk_summary must be a string.",
        "likely_regression_surface must be an array of strings.",
        "missing_verification must be an array of strings.",
        "suggested_follow_up_cases must be an array of objects with title, intent, priority, runner_goal, expected, recommended_checks, changed_files.",
        "findings must be an array of objects with severity, title, summary, changed_files, knowledge_case_ids, recommended_checks.",
        "If a field has no content, return an empty string or empty array instead of omitting it.",
        'Example valid JSON: {"risk_summary":"Lifecycle regression risk around async UI update.","likely_regression_surface":["Fragment view recreation","Null-safety around restored state"],"missing_verification":["Rotate screen during fetch and confirm no crash.","Navigate away before fetch completes and confirm no binding access after onDestroyView."],"suggested_follow_up_cases":[{"title":"Fragment recreation during async load","intent":"Verify the screen does not crash when the fragment view is recreated while profile data is loading.","priority":"high","runner_goal":"Open the profile screen, trigger profile loading, recreate the screen while loading, and confirm the UI stays stable without crashing.","expected":["The app does not crash during recreation.","The profile screen remains usable after loading resumes."],"recommended_checks":["Rotate device during fetch.","Assert no NullPointerException occurs."],"changed_files":["app/src/main/java/com/example/profile/ProfileFragment.kt"]}],"findings":[{"severity":"high","title":"Unsafe non-null assertion inside async callback","summary":"The async block dereferences nullable state with !! after suspension, which can crash if the state is absent when the callback resumes.","changed_files":["app/src/main/java/com/example/profile/ProfileFragment.kt"],"knowledge_case_ids":["android-kotlin-null-safety-bad-case"],"recommended_checks":["Replace !! with explicit null handling.","Add a lifecycle-aware regression test."]}]}',
    ]
)


class PydanticReviewAgent:
    def __init__(
        self,
        *,
        model: Any,
        output_strategy: OutputStrategy = "auto",
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> None:
        output_spec = build_structured_output_spec(ReviewResultDraft, output_strategy=output_strategy)
        self._agent = Agent(
            model=cast(Any, model),
            output_type=output_spec.output_type,
            system_prompt=append_system_prompt_suffix(SYSTEM_PROMPT, output_spec.system_prompt_suffix),
            name="pydantic_review_agent",
            output_retries=2,
            model_settings={
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )

    def review(self, *, prompt: str) -> ReviewResultDraft:
        result = self._agent.run_sync(prompt)
        return result.output
