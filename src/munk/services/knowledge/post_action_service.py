from __future__ import annotations

import json
from pathlib import Path

from munk.app_knowledge import (
    KnowledgeSubmitCandidateRequest,
    create_knowledge_runtime,
)
from munk.config.load import load_config_context
from munk.judging import JudgeResult
from munk.knowledge import KnowledgeManagedPaths, KnowledgeRuntimeContext
from munk.knowledge_agent.models import (
    KnowledgeAgentEvidenceBundle,
    KnowledgeAgentManagedPaths,
    KnowledgeAgentRequest,
    KnowledgeAgentRuntimeContext,
    KnowledgeArtifactRef,
)
from munk.services.operations.service import OperationCommandResult, OperationTracker

from ..knowledge_agent_runtime import resolve_knowledge_agent_runtime
from .request_models import KnowledgePostActionRequest, KnowledgePostActionResult


class KnowledgePostActionService:
    def execute(
        self,
        *,
        tracker: OperationTracker,
        request: KnowledgePostActionRequest,
    ) -> KnowledgePostActionResult:
        paths = _KnowledgePostActionPaths.from_run_dir(request.run_dir)
        paths.root_dir.mkdir(parents=True, exist_ok=True)
        paths.request_path.write_text(request.model_dump_json(indent=2), encoding="utf-8")
        judge_result = self._load_judge_result(request.judge_result_path)
        if judge_result is None:
            return self._write_skip_result(paths, summary="knowledge post action skipped: no judge result", skip_reason="no_judge_result")
        resolved_config = load_config_context(None, workspace_root=Path.cwd())
        agent_runtime = resolve_knowledge_agent_runtime(resolved_config=resolved_config)
        agent_output = agent_runtime.generate_candidates(
            KnowledgeAgentRequest(
                app_id=request.app_id,
                plan_id=request.plan_id,
                case_id=request.case_id,
                case_title=request.case_title,
                run_dir=request.run_dir,
                evidence_bundle=KnowledgeAgentEvidenceBundle(
                    judge_result=judge_result,
                    judge_result_path=request.judge_result_path,
                    artifacts=[
                        KnowledgeArtifactRef(artifact_id=artifact_id, path=path)
                        for artifact_id, path in sorted(request.artifact_paths.items())
                    ],
                ),
            ),
            context=KnowledgeAgentRuntimeContext(
                operation_id=tracker.operation_id,
                managed_paths=KnowledgeAgentManagedPaths(
                    root_dir=paths.root_dir,
                    prompt_path=paths.prompt_path,
                    tool_calls_path=paths.tool_calls_path,
                    llm_transcript_path=paths.llm_transcript_path,
                ),
            ),
        )
        if not agent_output.candidate_submissions:
            return self._write_skip_result(
                paths,
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
        runtime = create_knowledge_runtime(resolved_config={"app_registry_root": request.assets_root})
        runtime_context = KnowledgeRuntimeContext(
            operation_id=tracker.operation_id,
            managed_paths=KnowledgeManagedPaths(root_dir=paths.root_dir),
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
            return self._write_skip_result(paths, summary="knowledge post action skipped: submit returned empty record", skip_reason="empty_record")
        primary_record = submitted_records[0]
        tracker.append_event(
            event_type="knowledge_candidate_submitted",
            message="knowledge candidate submitted for pending review",
            data={
                "candidate_id": primary_record.candidate_id,
                "candidate_count": len(submitted_records),
                "case_id": request.case_id,
                "card_type": primary_record.candidate.card_type,
                "judge_verdict": judge_result.verdict,
            },
        )
        result = KnowledgePostActionResult(
            summary=agent_output.summary,
            submitted=True,
            candidate_id=primary_record.candidate_id,
            result_path=paths.result_path,
            request_path=paths.request_path,
            diagnostics_path=paths.diagnostics_path,
            artifacts={
                "knowledge_post_action_request": str(paths.request_path),
                "knowledge_post_action_result": str(paths.result_path),
                "knowledge_post_action_diagnostics": str(paths.diagnostics_path),
                **agent_output.artifacts,
            },
        )
        paths.result_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        paths.diagnostics_path.write_text(
            json.dumps(
                {
                    "status": "succeeded",
                    "submitted": True,
                    "candidate_ids": [record.candidate_id for record in submitted_records],
                    "judge_verdict": judge_result.verdict,
                    "tool_calls": list(agent_output.tool_calls),
                    "tool_call_count": len(agent_output.tool_calls),
                    "generated_candidate_count": len(agent_output.candidate_submissions),
                    "submitted_candidate_count": len(submitted_records),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return result

    def execute_command(
        self,
        *,
        tracker: OperationTracker,
        request: KnowledgePostActionRequest,
    ) -> OperationCommandResult:
        result = self.execute(tracker=tracker, request=request)
        paths = _KnowledgePostActionPaths.from_run_dir(request.run_dir)
        data = {
            "summary": result.summary,
            "submitted": result.submitted,
            "skip_reason": result.skip_reason,
            "candidate_id": result.candidate_id,
            "knowledge_post_action_result_path": str(result.result_path),
            "knowledge_post_action_request_path": str(result.request_path),
            "knowledge_post_action_diagnostics_path": str(result.diagnostics_path),
            "knowledge_post_action_tool_calls_path": str(paths.tool_calls_path),
        }
        return OperationCommandResult(
            data=data,
            artifacts=dict(result.artifacts),
            verification_verdict=None,
            result_json={**data, "artifacts": result.artifacts},
            status="succeeded",
        )

    @staticmethod
    def _load_judge_result(path: Path | None) -> JudgeResult | None:
        if path is None or not path.exists() or not path.is_file():
            return None
        return JudgeResult.model_validate(json.loads(path.read_text(encoding="utf-8")))

    @staticmethod
    def _write_skip_result(
        paths: "_KnowledgePostActionPaths",
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
            result_path=paths.result_path,
            request_path=paths.request_path,
            diagnostics_path=paths.diagnostics_path,
            artifacts={
                "knowledge_post_action_request": str(paths.request_path),
                "knowledge_post_action_result": str(paths.result_path),
                "knowledge_post_action_diagnostics": str(paths.diagnostics_path),
                **(extra_artifacts or {}),
            },
        )
        paths.result_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        paths.diagnostics_path.write_text(
            json.dumps(
                diagnostics_payload
                or {"status": "skipped", "skip_reason": skip_reason, "submitted": False},
                indent=2,
            ),
            encoding="utf-8",
        )
        return result


class _KnowledgePostActionPaths:
    def __init__(self, *, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.request_path = root_dir / "knowledge_post_action_request.json"
        self.result_path = root_dir / "knowledge_post_action_result.json"
        self.diagnostics_path = root_dir / "knowledge_post_action_diagnostics.json"
        self.tool_calls_path = root_dir / "knowledge_post_action_tool_calls.json"
        self.prompt_path = root_dir / "knowledge_post_action_prompt.txt"
        self.llm_transcript_path = root_dir / "knowledge_post_action_llm_transcript.json"

    @classmethod
    def from_run_dir(cls, run_dir: Path) -> "_KnowledgePostActionPaths":
        return cls(root_dir=run_dir / "knowledge")
