from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any, Protocol

from munk.agent_base.llm import llm_transcript_scope, summarize_llm_transcript_usage
from munk.agent_base.output_strategy import resolve_output_strategy
from munk.agent_base.pydantic_model_factory import build_pydantic_ai_model
from munk.agent_runtime.events import AgentRuntimeEventEmitter
from munk.judging.models import JudgeRequest, JudgeRuntimeContext, JudgeRuntimeOutput, JudgeRuntimeResultData

from munk.config import resolve_role_model_config

from .agent import PydanticAiJudgeAgent
from .agent_models import JudgeAgentOutput
from .errors import OperationCancelledError
from .evidence_builder import build_evidence_pack
from .models import JudgeEvidencePack
from .rules import apply_hard_rule_gate


class JudgeAgentLike(Protocol):
    def judge(self, evidence_pack: JudgeEvidencePack) -> JudgeAgentOutput: ...


class JudgeRuntimeService:
    def __init__(self, *, resolved_config: Any) -> None:
        judge_config = resolve_role_model_config(resolved_config.config, role="judge")
        if judge_config is None:
            raise ValueError("config must include a valid judge model configuration")
        model = build_pydantic_ai_model(judge_config, config=resolved_config.config)
        self._judge_agent = PydanticAiJudgeAgent(
            model=model,
            output_strategy=resolve_output_strategy(judge_config),
        )

    def judge(
        self,
        request: JudgeRequest,
        *,
        context: JudgeRuntimeContext,
        cancel_controller=None,  # noqa: ANN001
    ) -> JudgeRuntimeOutput:
        emitter = AgentRuntimeEventEmitter(
            agent_role="judge",
            operation_id=context.operation_id,
            event_sink=context.progress,
        )
        started_at = datetime.now(timezone.utc).isoformat()
        started = time.monotonic()
        emitter.emit_started(
            message="judge runtime started",
            data={"app_id": request.app_id, "case_id": request.case_id},
        )
        try:
            self._write_json(context.managed_paths.judge_request_path, request.model_dump(mode="json"))
            emitter.emit_progress(
                event_type="judge_context_loaded",
                message="judge context loaded",
                data={
                    "app_id": request.app_id,
                    "case_id": request.case_id,
                    "root_dir": str(context.managed_paths.root_dir),
                },
            )
            self._raise_if_cancelled(cancel_controller)
            evidence_pack = build_evidence_pack(request=request)
            hard_rule = apply_hard_rule_gate(request.execution, request.events, evidence_pack)
            if hard_rule is not None:
                result_data = JudgeRuntimeResultData(
                    verdict=hard_rule.verdict,
                    summary=hard_rule.summary,
                    reason=hard_rule.reason,
                    failure_hypothesis=hard_rule.failure_hypothesis,
                    supporting_evidence_ids=hard_rule.supporting_evidence_ids or [],
                    evidence=evidence_pack.evidence,
                )
                self._write_json(context.managed_paths.evidence_selection_path, {"mode": "hard_rule"})
                self._write_json(context.managed_paths.tool_calls_path, {"tool_calls": []})
                emitter.emit_progress(
                    event_type="judge_hard_rule_completed",
                    message="judge hard rule completed",
                    data={
                        "app_id": request.app_id,
                        "case_id": request.case_id,
                        "verdict": hard_rule.verdict,
                    },
                )
                output = JudgeRuntimeOutput(
                    result_data=result_data,
                    started_at=started_at,
                    duration_ms=int((time.monotonic() - started) * 1000),
                    tool_calls=[],
                    token_usage=summarize_llm_transcript_usage(context.managed_paths.llm_transcript_path),
                )
                emitter.emit_ended(
                    message="judge runtime completed",
                    data={
                        "app_id": request.app_id,
                        "case_id": request.case_id,
                        "verdict": output.result_data.verdict,
                        "tool_call_count": 0,
                    },
                )
                return output

            self._raise_if_cancelled(cancel_controller)
            with llm_transcript_scope(context.managed_paths.llm_transcript_path):
                agent_output = self._judge_agent.judge(evidence_pack)
            tool_calls = self._judge_agent.last_tool_calls
            self._write_json(
                context.managed_paths.evidence_selection_path,
                {
                    "mode": "runtime",
                    "primary_evidence_ids": [item.evidence_id for item in evidence_pack.primary_evidence],
                    "supporting_evidence_ids": [item.evidence_id for item in evidence_pack.supporting_evidence],
                },
            )
            self._write_json(context.managed_paths.tool_calls_path, {"tool_calls": tool_calls})
            context.managed_paths.judge_prompt_path.write_text(self._judge_agent.last_prompt, encoding="utf-8")
            emitter.emit_progress(
                event_type="judge_agent_completed",
                message="judge agent completed",
                data={
                    "app_id": request.app_id,
                    "case_id": request.case_id,
                    "verdict": agent_output.verdict,
                    "tool_call_count": len(tool_calls),
                },
            )
            self._raise_if_cancelled(cancel_controller)
            output = JudgeRuntimeOutput(
                result_data=JudgeRuntimeResultData(
                    verdict=agent_output.verdict,
                    summary=agent_output.summary,
                    reason=agent_output.reason,
                    failure_hypothesis=agent_output.failure_hypothesis,
                    confidence=agent_output.confidence,
                    missing_evidence=agent_output.missing_evidence,
                    supporting_evidence_ids=agent_output.supporting_evidence_ids,
                    evidence=evidence_pack.evidence,
                    needs_optimization=agent_output.needs_optimization,
                    optimization_fields=list(agent_output.optimization_fields),
                    optimization_reason=agent_output.optimization_reason,
                    optimization_confidence=agent_output.optimization_confidence,
                ),
                started_at=started_at,
                duration_ms=int((time.monotonic() - started) * 1000),
                tool_calls=tool_calls,
                token_usage=summarize_llm_transcript_usage(context.managed_paths.llm_transcript_path),
            )
        except OperationCancelledError:
            emitter.emit_canceled(
                message="judge runtime canceled",
                data={"app_id": request.app_id, "case_id": request.case_id},
            )
            raise
        except Exception as exc:
            emitter.emit_failed(
                message="judge runtime failed",
                data={
                    "app_id": request.app_id,
                    "case_id": request.case_id,
                    "error_type": exc.__class__.__name__,
                },
            )
            raise
        emitter.emit_ended(
            message="judge runtime completed",
            data={
                "app_id": request.app_id,
                "case_id": request.case_id,
                "verdict": output.result_data.verdict,
                "tool_call_count": len(output.tool_calls),
            },
        )
        return output

    @staticmethod
    def _write_json(path, payload: dict[str, object]) -> None:  # noqa: ANN001
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    @staticmethod
    def _raise_if_cancelled(cancel_controller) -> None:  # noqa: ANN001
        if cancel_controller is not None and cancel_controller.is_cancel_requested():
            raise OperationCancelledError("operation cancelled cooperatively")
