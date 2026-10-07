from __future__ import annotations

import json
from datetime import datetime, timezone

from munk.agent_base.llm import llm_transcript_scope
from munk.agent_base.output_strategy import resolve_output_strategy
from munk.agent_runtime.control import CancelController
from munk.agent_runtime.events import AgentRuntimeEventEmitter
from munk.reviewing.models import (
    ReviewFinding,
    ReviewKnowledgeHit,
    ReviewRequest,
    SuggestedFollowUpCase,
)
from munk.reviewing.runtime import (
    ReviewRuntimeContext,
    ReviewRuntimeOutput,
    ReviewRuntimeResultData,
)

from munk.config import resolve_role_model_config

from .errors import OperationCancelledError
from .model_factory import build_review_model
from .orchestration_service import ReviewOrchestrationService
from .pydantic_review_agent import PydanticReviewAgent
from .retrieval_service import ReviewRetrievalService
from .review_agent_models import ReviewResultDraft
from .runtime_support import elapsed_ms, timer

REVIEW_PROMPT_HITS_TOP_N = 4
REVIEW_PROMPT_HITS_MIN_SCORE = 0.20


class ReviewService:
    def __init__(
        self,
        *,
        resolved_config,
        retrieval_service: ReviewRetrievalService | None = None,
        artifact_manifest_service=None,
    ) -> None:
        self._resolved_config = resolved_config
        self._retrieval_service = retrieval_service or ReviewRetrievalService()
        del artifact_manifest_service

    def review(
        self,
        request: ReviewRequest,
        *,
        context: ReviewRuntimeContext,
        cancel_controller: CancelController | None = None,
    ) -> ReviewRuntimeOutput:
        emitter = AgentRuntimeEventEmitter(
            agent_role="review",
            operation_id=context.operation_id,
            event_sink=context.progress,
        )
        started_at = datetime.now(timezone.utc).isoformat()
        timer_start = timer()
        emitter.emit_started(
            message="review runtime started",
            data={"app_id": request.app_id},
        )
        try:
            paths = context.managed_paths
            paths.review_request_path.write_text(
                request.model_dump_json(indent=2),
                encoding="utf-8",
            )
            emitter.emit_progress(
                event_type="review_context_loaded",
                message="review context loaded",
                data={"app_id": request.app_id, "root_dir": str(paths.root_dir)},
            )
            warning_summary: list[str] = []
            retrieval = None
            prompt_hits: list[ReviewKnowledgeHit] = []
            self._raise_if_cancelled(cancel_controller)
            query_text = self._build_query_text(request)
            retrieval = self._retrieval_service.retrieve(request=request, query_text=query_text)
            prompt_hits = self._select_prompt_hits(retrieval.hits)
            paths.retrieval_path.write_text(
                json.dumps(
                    {
                        **retrieval.debug_payload,
                        "knowledge_hits": [hit.model_dump(mode="json") for hit in retrieval.hits],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            if not retrieval.hits:
                warning_summary.append("no knowledge hits were retrieved")
            emitter.emit_progress(
                event_type="review_retrieval_completed",
                message="review retrieval completed",
                data={
                    "app_id": request.app_id,
                    "retrieval_hit_count": len(retrieval.hits),
                    "prompt_hit_count": len(prompt_hits),
                },
            )
            self._raise_if_cancelled(cancel_controller)
            with llm_transcript_scope(paths.llm_transcript_path):
                draft = self._build_review_agent(request).review(
                    prompt=self._build_prompt(request=request, query_text=query_text, hits=prompt_hits)
                )
            emitter.emit_progress(
                event_type="review_agent_completed",
                message="review agent completed",
                data={
                    "app_id": request.app_id,
                    "finding_count": len(draft.findings),
                    "suggested_case_count": len(draft.suggested_follow_up_cases),
                },
            )
            self._raise_if_cancelled(cancel_controller)
            result_data = self._build_result_data(
                request=request,
                draft=draft,
                hits=retrieval.hits,
            )
            orchestration_contract = ReviewOrchestrationService().build_bundle(
                result_data=result_data,
                app_id=request.app_id,
            ).contract
            output = ReviewRuntimeOutput(
                result_data=result_data,
                review_orchestration=orchestration_contract,
                started_at=started_at,
                duration_ms=elapsed_ms(timer_start),
                warning_summary=warning_summary,
                prompt_hits=prompt_hits,
                retrieval_debug_payload=dict(retrieval.debug_payload),
            )
        except OperationCancelledError:
            emitter.emit_canceled(
                message="review runtime canceled",
                data={"app_id": request.app_id},
            )
            raise
        except Exception as exc:
            emitter.emit_failed(
                message="review runtime failed",
                data={
                    "app_id": request.app_id,
                    "error_type": exc.__class__.__name__,
                },
            )
            raise
        emitter.emit_ended(
            message="review runtime completed",
            data={
                "app_id": request.app_id,
                "finding_count": output.result_data.finding_count,
                "warning_count": len(output.warning_summary),
            },
        )
        return output

    @staticmethod
    def _raise_if_cancelled(cancel_controller: CancelController | None) -> None:
        if cancel_controller is not None and cancel_controller.is_cancel_requested():
            raise OperationCancelledError("operation cancelled cooperatively")

    @staticmethod
    def _select_prompt_hits(hits: list[ReviewKnowledgeHit]) -> list[ReviewKnowledgeHit]:
        if not hits:
            return []
        top_hits = hits[:REVIEW_PROMPT_HITS_TOP_N]
        filtered_hits = [
            hit
            for hit in top_hits
            if hit.combined_score is not None and hit.combined_score >= REVIEW_PROMPT_HITS_MIN_SCORE
        ]
        return filtered_hits or top_hits[:1]

    def _build_review_agent(self, request: ReviewRequest) -> PydanticReviewAgent:
        del request
        model = build_review_model(resolved_config=self._resolved_config)
        resolved = resolve_role_model_config(self._resolved_config.config, role="review")
        return PydanticReviewAgent(
            model=model,
            output_strategy=resolve_output_strategy(resolved),
        )

    @staticmethod
    def _build_query_text(request: ReviewRequest) -> str:
        parts = []
        if request.change_summary and request.change_summary.strip():
            parts.append("Change summary:\n" + request.change_summary.strip())
        if request.changed_files:
            parts.append("Changed files:\n" + "\n".join(request.changed_files))
        if request.review_query and request.review_query.strip():
            parts.append("Review query:\n" + request.review_query.strip())
        if request.diff_text and request.diff_text.strip():
            parts.append("Diff:\n" + request.diff_text.strip())
        for label, path in (
            ("Requirement document", request.requirement_doc_path),
            ("Technical document", request.technical_doc_path),
        ):
            if path is None:
                continue
            text = path.read_text(encoding="utf-8").strip()
            if text:
                parts.append(f"{label}:\n{text}")
        return "\n\n".join(parts).strip()

    @staticmethod
    def _build_prompt(
        *,
        request: ReviewRequest,
        query_text: str,
        hits: list[ReviewKnowledgeHit],
    ) -> str:
        knowledge_section = "\n\n".join(
            [
                "\n".join(
                    [
                        f"case_id: {hit.case_id}",
                        f"platform: {hit.platform}",
                        f"domain: {hit.domain}",
                        f"topic: {hit.topic}",
                        f"case_type: {hit.case_type}",
                        f"title: {hit.title}",
                        f"summary: {hit.summary}",
                        f"recommended_checks: {', '.join(hit.recommended_checks) if hit.recommended_checks else 'none'}",
                        "body_excerpt:",
                        hit.body_excerpt or "none",
                    ]
                )
                for hit in hits
            ]
        ) or "No relevant knowledge cards were retrieved."
        return "\n\n".join(
            [
                "Review the following code change and produce a structured review result.",
                f"App ID: {request.app_id or 'none'}",
                "Change Context:\n" + query_text,
                "Retrieved Knowledge Cards:\n" + knowledge_section,
                "\n".join(
                    [
                        "Review requirements:",
                        "- Keep findings grounded in the changed scope.",
                        "- Use severity levels low/medium/high/critical.",
                        "- Populate knowledge_case_ids when a finding is supported by retrieved knowledge.",
                        "- missing_verification should describe checks that still need to be run.",
                        "- suggested_follow_up_cases should be executable follow-up ideas, not vague advice.",
                        "- Use priority=high only for must-run cases that should be validated before any broader supplemental planning.",
                        "- Every suggested_follow_up_case must include runner_goal and expected results suitable for downstream execution planning.",
                    ]
                ),
            ]
        )

    @staticmethod
    def _build_result_data(
        *,
        request: ReviewRequest,
        draft: ReviewResultDraft,
        hits: list[ReviewKnowledgeHit],
    ) -> ReviewRuntimeResultData:
        findings = [
            ReviewFinding(
                severity=item.severity,
                title=item.title,
                summary=item.summary,
                changed_files=list(item.changed_files),
                knowledge_case_ids=list(item.knowledge_case_ids),
                recommended_checks=list(item.recommended_checks),
            )
            for item in draft.findings
        ]
        suggested_cases = [
            SuggestedFollowUpCase(
                title=item.title,
                intent=item.intent,
                priority=item.priority,
                runner_goal=item.runner_goal,
                expected=list(item.expected),
                recommended_checks=list(item.recommended_checks),
                changed_files=list(item.changed_files),
            )
            for item in draft.suggested_follow_up_cases
        ]
        high_risk_count = sum(1 for item in findings if item.severity in {"high", "critical"})
        del high_risk_count
        return ReviewRuntimeResultData(
            app_id=request.app_id,
            risk_summary=draft.risk_summary,
            likely_regression_surface=list(draft.likely_regression_surface),
            missing_verification=list(draft.missing_verification),
            suggested_follow_up_cases=suggested_cases,
            findings=findings,
            knowledge_hits=hits,
        )
