from __future__ import annotations

import json
from pathlib import Path

from munk.agent_base.llm import llm_transcript_observer_scope
from munk.app_knowledge import KnowledgeSubmitCandidateRequest, create_knowledge_runtime
from munk.config import ResolvedConfig
from munk.execution.models import CaseExecutionResult
from munk.knowledge import KnowledgeManagedPaths, KnowledgeRuntimeContext
from munk.knowledge_agent.models import KnowledgeAgentManagedPaths, KnowledgeAgentRuntimeContext
from munk.services.operations.runtime_event_sinks import TrackerAgentRuntimeTimelineSink
from munk.services.operations.llm_timeline import build_llm_timeline_observer
from munk.services.operations.service import OperationCommandResult, OperationTracker
from munk.services.post_run_analysis import (
    build_knowledge_agent_request,
    build_post_run_analysis_agent_input,
    resolve_case_run_evidence,
)

from ..knowledge_agent_runtime import resolve_knowledge_agent_runtime
from .materializer import KnowledgePostActionMaterializer
from .operation_payloads import build_knowledge_post_action_operation_result_payload
from .request_models import KnowledgePostActionOperationRequest, KnowledgePostActionResult


class KnowledgePostActionOperationService:
    def __init__(self, *, resolved_config: ResolvedConfig) -> None:
        self._resolved_config = resolved_config
        self._materializer = KnowledgePostActionMaterializer()

    def execute(
        self,
        *,
        tracker: OperationTracker,
        request: KnowledgePostActionOperationRequest,
    ) -> KnowledgePostActionResult:
        paths = self._materializer.paths(run_dir=request.run_dir)
        tracker.append_timeline_event(
            event_type="knowledge_started",
            message="knowledge post action started",
            agent_role="knowledge",
            timeline_scope="child_operation",
            timeline_phase="started",
            summary="knowledge post action started",
            attempt_index=request.source_attempt_index,
            parent_operation_id=request.parent_operation_id,
            app_id=request.app_id,
            plan_id=request.plan_id,
            case_id=request.case_id,
        )
        case_result = CaseExecutionResult.model_validate(
            json.loads(request.result_path.read_text(encoding="utf-8"))
        )
        evidence = resolve_case_run_evidence(
            case_result,
            judge_result_path=request.judge_result_path,
            prefer_optimization_attempt=False,
        )
        agent_input = build_post_run_analysis_agent_input(
            evidence,
            app_id=request.app_id,
            case_title=request.case_title,
        )
        paths["request"].write_text(request.model_dump_json(indent=2), encoding="utf-8")
        self._materializer.write_agent_input(paths["agent_input"], agent_input)
        tracker.append_timeline_event(
            event_type="knowledge_agent_input_ready",
            message="knowledge agent input ready",
            agent_role="knowledge",
            timeline_scope="child_operation",
            timeline_phase="context_loaded",
            summary="knowledge agent input ready",
            attempt_index=evidence.source_attempt_index,
            parent_operation_id=request.parent_operation_id,
            app_id=request.app_id,
            plan_id=request.plan_id,
            case_id=request.case_id,
            data={"agent_input_path": str(paths["agent_input"])},
        )

        if evidence.judge_result is None:
            return self._write_skip_result(
                tracker=tracker,
                request=request,
                attempt_index=evidence.source_attempt_index,
                paths=paths,
                summary="knowledge post action skipped: no judge result",
                skip_reason="no_judge_result",
            )
        if evidence.judge_result.verdict == "passed":
            return self._write_skip_result(
                tracker=tracker,
                request=request,
                attempt_index=evidence.source_attempt_index,
                paths=paths,
                summary="knowledge post action skipped: passed case",
                skip_reason="verdict_passed",
            )

        agent_runtime = resolve_knowledge_agent_runtime(resolved_config=self._resolved_config)
        knowledge_request = build_knowledge_agent_request(agent_input, evidence)
        runtime_context = KnowledgeAgentRuntimeContext(
            operation_id=tracker.operation_id,
            attempt_index=evidence.source_attempt_index,
            managed_paths=KnowledgeAgentManagedPaths(
                root_dir=paths["root"],
                prompt_path=paths["prompt"],
                tool_calls_path=paths["tool_calls"],
                llm_transcript_path=paths["llm_transcript"],
            ),
            progress=TrackerAgentRuntimeTimelineSink(tracker),
        )
        llm_observer = build_llm_timeline_observer(
            tracker=tracker,
            agent_role="knowledge",
            attempt_index=evidence.source_attempt_index,
            app_id=request.app_id,
            plan_id=request.plan_id,
            case_id=request.case_id,
            timeline_scope="child_operation",
            parent_operation_id=request.parent_operation_id,
        )
        with llm_transcript_observer_scope(llm_observer):
            agent_output = agent_runtime.generate_candidates(
                knowledge_request,
                context=runtime_context,
            )
        tracker.append_timeline_event(
            event_type="knowledge_runtime_completed",
            message="knowledge runtime completed",
            agent_role="knowledge",
            timeline_scope="child_operation",
            timeline_phase="result_ready",
            summary=agent_output.summary,
            attempt_index=evidence.source_attempt_index,
            parent_operation_id=request.parent_operation_id,
            app_id=request.app_id,
            plan_id=request.plan_id,
            case_id=request.case_id,
            data={"tool_call_count": len(agent_output.tool_calls)},
        )
        if not agent_output.candidate_submissions:
            return self._write_skip_result(
                tracker=tracker,
                request=request,
                attempt_index=evidence.source_attempt_index,
                paths=paths,
                summary=agent_output.summary,
                skip_reason=agent_output.skip_reason or "no_candidate_generated",
                extra_artifacts=agent_output.artifacts,
                diagnostics_payload={
                    "status": "skipped",
                    "skip_reason": agent_output.skip_reason or "no_candidate_generated",
                    "submitted": False,
                    "tool_calls": list(agent_output.tool_calls),
                    "tool_call_count": len(agent_output.tool_calls),
                    "generated_candidate_count": 0,
                },
            )

        runtime = create_knowledge_runtime(
            resolved_config={"app_registry_root": request.assets_root},
        )
        runtime_context = KnowledgeRuntimeContext(
            operation_id=tracker.operation_id,
            managed_paths=KnowledgeManagedPaths(root_dir=paths["root"]),
        )
        submitted_records = []
        for submission in agent_output.candidate_submissions:
            output = runtime.submit_candidate(
                KnowledgeSubmitCandidateRequest(submission=submission),
                context=runtime_context,
            )
            if output.candidate is not None:
                submitted_records.append(output.candidate)
        if not submitted_records:
            return self._write_skip_result(
                tracker=tracker,
                request=request,
                attempt_index=evidence.source_attempt_index,
                paths=paths,
                summary="knowledge post action skipped: submit returned empty record",
                skip_reason="empty_record",
            )

        primary_record = submitted_records[0]
        tracker.append_timeline_event(
            event_type="knowledge_candidate_submission_completed",
            message="knowledge candidate submitted for pending review",
            agent_role="knowledge",
            timeline_scope="child_operation",
            timeline_phase="completed",
            summary="knowledge candidate submitted for pending review",
            attempt_index=evidence.source_attempt_index,
            parent_operation_id=request.parent_operation_id,
            app_id=request.app_id,
            plan_id=request.plan_id,
            case_id=request.case_id,
            data={
                "candidate_id": primary_record.candidate_id,
                "candidate_count": len(submitted_records),
                "case_id": request.case_id,
                "card_type": primary_record.candidate.card_type,
                "judge_verdict": evidence.judge_result.verdict,
            },
        )
        result = KnowledgePostActionResult(
            summary=agent_output.summary,
            submitted=True,
            candidate_id=primary_record.candidate_id,
            result_path=paths["result"],
            request_path=paths["request"],
            diagnostics_path=paths["diagnostics"],
            artifacts={
                "knowledge_post_action_request": str(paths["request"]),
                "knowledge_post_action_agent_input": str(paths["agent_input"]),
                "knowledge_post_action_result": str(paths["result"]),
                "knowledge_post_action_diagnostics": str(paths["diagnostics"]),
                **agent_output.artifacts,
            },
        )
        paths["result"].write_text(result.model_dump_json(indent=2), encoding="utf-8")
        self._materializer.write_diagnostics(
            paths["diagnostics"],
            {
                "status": "succeeded",
                "submitted": True,
                "candidate_ids": [record.candidate_id for record in submitted_records],
                "judge_verdict": evidence.judge_result.verdict,
                "tool_calls": list(agent_output.tool_calls),
                "tool_call_count": len(agent_output.tool_calls),
                "generated_candidate_count": len(agent_output.candidate_submissions),
                "submitted_candidate_count": len(submitted_records),
            },
        )
        tracker.append_timeline_event(
            event_type="knowledge_result_ready",
            message="knowledge result ready",
            agent_role="knowledge",
            timeline_scope="child_operation",
            timeline_phase="result_ready",
            summary=result.summary,
            attempt_index=evidence.source_attempt_index,
            parent_operation_id=request.parent_operation_id,
            app_id=request.app_id,
            plan_id=request.plan_id,
            case_id=request.case_id,
            data={"candidate_id": result.candidate_id, "submitted": True},
        )
        tracker.append_timeline_event(
            event_type="knowledge_completed",
            message="knowledge post action completed",
            agent_role="knowledge",
            timeline_scope="child_operation",
            timeline_phase="completed",
            summary=result.summary,
            attempt_index=evidence.source_attempt_index,
            parent_operation_id=request.parent_operation_id,
            app_id=request.app_id,
            plan_id=request.plan_id,
            case_id=request.case_id,
            data={"submitted": True, "candidate_id": result.candidate_id},
        )
        return result

    def execute_command(
        self,
        *,
        tracker: OperationTracker,
        request: KnowledgePostActionOperationRequest,
    ) -> OperationCommandResult:
        result = self.execute(tracker=tracker, request=request)
        paths = self._materializer.paths(run_dir=request.run_dir)
        payload = build_knowledge_post_action_operation_result_payload(
            result,
            tool_calls_path=str(paths["tool_calls"]),
        )
        return OperationCommandResult(
            data=payload.to_command_data(),
            artifacts=dict(result.artifacts),
            verification_verdict=None,
            result_json=payload.model_dump(mode="json"),
            status="succeeded",
        )

    @staticmethod
    def _write_skip_result(
        tracker: OperationTracker,
        request: KnowledgePostActionOperationRequest,
        attempt_index: int | None,
        paths: dict[str, Path],
        *,
        summary: str,
        skip_reason: str,
        extra_artifacts: dict[str, str] | None = None,
        diagnostics_payload: dict[str, object] | None = None,
    ) -> KnowledgePostActionResult:
        result = KnowledgePostActionResult(
            summary=summary,
            submitted=False,
            skip_reason=skip_reason,
            result_path=paths["result"],
            request_path=paths["request"],
            diagnostics_path=paths["diagnostics"],
            artifacts={
                "knowledge_post_action_request": str(paths["request"]),
                "knowledge_post_action_agent_input": str(paths["agent_input"]),
                "knowledge_post_action_result": str(paths["result"]),
                "knowledge_post_action_diagnostics": str(paths["diagnostics"]),
                **(extra_artifacts or {}),
            },
        )
        paths["result"].write_text(result.model_dump_json(indent=2), encoding="utf-8")
        KnowledgePostActionMaterializer.write_diagnostics(
            paths["diagnostics"],
            diagnostics_payload
            or {"status": "skipped", "skip_reason": skip_reason, "submitted": False},
        )
        tracker.append_timeline_event(
            event_type="knowledge_skipped",
            message=summary,
            agent_role="knowledge",
            timeline_scope="child_operation",
            timeline_phase="skipped",
            summary=summary,
            attempt_index=attempt_index,
            parent_operation_id=request.parent_operation_id,
            app_id=request.app_id,
            plan_id=request.plan_id,
            case_id=request.case_id,
            data={"skip_reason": skip_reason, "submitted": False},
        )
        return result


KnowledgePostActionService = KnowledgePostActionOperationService
