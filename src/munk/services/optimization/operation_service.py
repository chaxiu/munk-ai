from __future__ import annotations

import json

from munk.agent_base.llm import llm_transcript_observer_scope
from munk.config import ResolvedConfig
from munk.execution.models import CaseExecutionResult
from munk.optimizing import (
    OptimizeExecutionSummary,
    OptimizeFieldPatch,
    OptimizeManagedPaths,
    OptimizeRequest,
    OptimizeRuntimeContext,
    OptimizeTrigger,
)
from munk.planning.plan_mutation_service import PlanMutationService
from munk.planning.storage import PlanStore
from munk.services.operations.runtime_event_sinks import TrackerAgentRuntimeTimelineSink
from munk.services.operations.llm_timeline import build_llm_timeline_observer
from munk.services.operations.service import OperationCommandResult, OperationTracker
from munk.services.optimize_runtime import resolve_optimize_runtime
from munk.services.post_run_analysis import (
    build_post_run_analysis_agent_input,
    resolve_case_run_evidence,
)
from munk.testing import AiGuidance

from .materializer import OptimizeArtifactMaterializer, OptimizeFieldDiffBundle, OptimizeFieldDiffItem
from .operation_payloads import build_optimize_case_operation_result_payload
from .policy import OptimizeCasePolicy
from .request_models import OptimizeCaseOperationRequest, OptimizeCaseOperationResult

MAX_GUIDANCE_ITEMS_PER_FIELD = 8
MAX_GUIDANCE_ITEM_LENGTH = 240


class OptimizeCaseOperationService:
    def __init__(
        self,
        *,
        resolved_config: ResolvedConfig,
        plan_store: PlanStore | None = None,
        mutation_service: PlanMutationService | None = None,
        policy: OptimizeCasePolicy | None = None,
    ) -> None:
        self._resolved_config = resolved_config
        self._plan_store = plan_store or PlanStore()
        self._mutation_service = mutation_service or PlanMutationService(plan_store=self._plan_store)
        self._materializer = OptimizeArtifactMaterializer()
        self._policy = policy or OptimizeCasePolicy()

    def execute(
        self,
        *,
        tracker: OperationTracker,
        request: OptimizeCaseOperationRequest,
    ) -> OptimizeCaseOperationResult:
        tracker.append_timeline_event(
            event_type="optimize_started",
            message="optimize case started",
            agent_role="optimize",
            timeline_scope="child_operation",
            timeline_phase="started",
            summary="optimize case started",
            attempt_index=request.trigger.source_attempt_index,
            parent_operation_id=request.parent_operation_id,
            app_id=request.app_id,
            plan_id=request.plan_id,
            case_id=request.case_id,
        )
        case_result = CaseExecutionResult.model_validate(
            json.loads(request.result_path.read_text(encoding="utf-8"))
        )
        evidence = resolve_case_run_evidence(case_result, judge_result_path=request.judge_result_path)
        trigger = request.trigger.trigger
        source_attempt_index = request.trigger.source_attempt_index
        if source_attempt_index is None:
            source_attempt_index = evidence.source_attempt_index
        plan = self._plan_store.load(request.app_id, request.plan_id)
        case = next(item for item in plan.cases if item.case_id == request.case_id)
        agent_input = build_post_run_analysis_agent_input(
            evidence,
            app_id=request.app_id,
            case_title=case.title,
        )
        optimize_request = OptimizeRequest(
            app_id=request.app_id,
            plan_id=request.plan_id,
            case_id=request.case_id,
            case_title=case.title,
            intent=case.intent,
            runner_goal=case.runner_goal,
            expected=list(case.expected),
            current_ai_guidance=case.ai_guidance.model_copy(deep=True) if case.ai_guidance is not None else None,
            execution_summary=OptimizeExecutionSummary(
                verdict=case_result.verdict,
                summary=case_result.summary,
                judge_reason=case_result.judge_reason,
                attempt_count=case_result.attempt_count,
                retry_count=max(0, case_result.attempt_count - 1),
            ),
            trigger=OptimizeTrigger(
                needs_optimization=trigger.needs_optimization,
                optimization_fields=list(trigger.optimization_fields),
                optimization_reason=trigger.optimization_reason,
                optimization_confidence=trigger.optimization_confidence,
                source=request.trigger.trigger_source,
                signals=list(request.trigger.trigger_signals),
                source_attempt_index=source_attempt_index,
            ),
            artifacts=dict(evidence.artifacts),
            structured_evidence=dict(agent_input.structured_evidence),
            run_dir=request.run_dir,
        )
        paths = self._materializer.paths(run_dir=request.run_dir)
        self._materializer.write_request(paths["request"], optimize_request)
        tracker.append_timeline_event(
            event_type="optimize_request_built",
            message="optimize request built",
            agent_role="optimize",
            timeline_scope="child_operation",
            timeline_phase="context_loaded",
            summary="optimize request built",
            attempt_index=source_attempt_index,
            parent_operation_id=request.parent_operation_id,
            app_id=request.app_id,
            plan_id=request.plan_id,
            case_id=request.case_id,
            data={"request_path": str(paths["request"])},
        )
        runtime = resolve_optimize_runtime(resolved_config=self._resolved_config)
        runtime_context = OptimizeRuntimeContext(
            operation_id=tracker.operation_id,
            managed_paths=OptimizeManagedPaths(
                root_dir=paths["root"],
                prompt_path=paths["prompt"],
                tool_calls_path=paths["tool_calls"],
                llm_transcript_path=paths["llm_transcript"],
            ),
            attempt_index=source_attempt_index,
            progress=TrackerAgentRuntimeTimelineSink(tracker),
        )
        llm_observer = build_llm_timeline_observer(
            tracker=tracker,
            agent_role="optimize",
            attempt_index=source_attempt_index,
            app_id=request.app_id,
            plan_id=request.plan_id,
            case_id=request.case_id,
            timeline_scope="child_operation",
            parent_operation_id=request.parent_operation_id,
        )
        with llm_transcript_observer_scope(llm_observer):
            result = runtime.optimize(optimize_request, context=runtime_context)
        tracker.append_timeline_event(
            event_type="optimize_runtime_completed",
            message="optimize runtime completed",
            agent_role="optimize",
            timeline_scope="child_operation",
            timeline_phase="result_ready",
            summary=result.summary,
            attempt_index=source_attempt_index,
            parent_operation_id=request.parent_operation_id,
            app_id=request.app_id,
            plan_id=request.plan_id,
            case_id=request.case_id,
            data={"patched_field_count": len(result.patched_fields)},
        )
        current_guidance = case.ai_guidance or AiGuidance()
        patches = self._filter_allowed_patches(
            result.patched_fields,
            allowed_fields=set(trigger.optimization_fields),
        )
        field_diffs = [
            OptimizeFieldDiffItem(
                field_name=patch.field_name,
                reason=patch.reason,
                before=self._guidance_field_items(current_guidance, patch.field_name),
                after=self._sanitize_guidance_items(list(patch.replace_with)),
                changed=self._guidance_field_items(current_guidance, patch.field_name)
                != self._sanitize_guidance_items(list(patch.replace_with)),
            )
            for patch in patches
        ]
        writeback_fields = {
            item.field_name: list(item.after)
            for item in field_diffs
            if item.changed
        }
        confidence = trigger.optimization_confidence
        applied = False
        skip_reason: str | None = None
        if not self._policy.should_apply_writeback(
            optimization_confidence=confidence,
            optimization_fields=list(trigger.optimization_fields),
        ):
            skip_reason = "low_confidence"
        elif not writeback_fields:
            skip_reason = "no_op"
        else:
            mutation = self._mutation_service.update_ai_guidance_fields(
                request.app_id,
                request.plan_id,
                request.case_id,
                replace_fields=writeback_fields,
            )
            tracker.append_timeline_event(
                event_type="optimize_applied",
                message="ai_guidance fields updated",
                agent_role="optimize",
                timeline_scope="child_operation",
                timeline_phase="applied",
                summary="ai_guidance fields updated",
                attempt_index=source_attempt_index,
                parent_operation_id=request.parent_operation_id,
                app_id=request.app_id,
                plan_id=request.plan_id,
                case_id=mutation.case.case_id,
                data={"patched_fields": sorted(writeback_fields)},
            )
            applied = True
        self._materializer.write_result(paths["result"], result)
        field_diff_bundle = OptimizeFieldDiffBundle(
            operation_id=tracker.operation_id,
            case_id=request.case_id,
            summary=result.summary,
            items=field_diffs,
        )
        self._materializer.write_field_diffs(paths["field_diffs"], field_diff_bundle)
        self._materializer.write_diagnostics(
            paths["diagnostics"],
            patched_fields=sorted(writeback_fields) if applied else [],
            status="succeeded",
            summary=result.summary,
            applied=applied,
            skip_reason=skip_reason,
            confidence=confidence,
            field_diff_count=len(field_diffs),
        )
        if skip_reason is not None:
            tracker.append_timeline_event(
                event_type="optimize_skipped",
                message="optimize case skipped",
                agent_role="optimize",
                timeline_scope="child_operation",
                timeline_phase="skipped",
                summary=f"optimize case skipped: {skip_reason}",
                attempt_index=source_attempt_index,
                parent_operation_id=request.parent_operation_id,
                app_id=request.app_id,
                plan_id=request.plan_id,
                case_id=request.case_id,
                data={"skip_reason": skip_reason},
            )
        artifacts = {
            "optimization_request": str(paths["request"]),
            "optimization_prompt": str(paths["prompt"]),
            "optimization_tool_calls": str(paths["tool_calls"]),
            "optimization_llm_transcript": str(paths["llm_transcript"]),
            "optimization_result": str(paths["result"]),
            "optimization_diagnostics": str(paths["diagnostics"]),
            "field_diffs": str(paths["field_diffs"]),
        }
        tracker.append_timeline_event(
            event_type="optimize_result_ready",
            message="optimize result ready",
            agent_role="optimize",
            timeline_scope="child_operation",
            timeline_phase="result_ready",
            summary=result.summary,
            attempt_index=source_attempt_index,
            parent_operation_id=request.parent_operation_id,
            app_id=request.app_id,
            plan_id=request.plan_id,
            case_id=request.case_id,
            data={
                "applied": applied,
                "skip_reason": skip_reason,
                "field_diff_count": len(field_diffs),
            },
        )
        tracker.append_timeline_event(
            event_type="optimize_completed",
            message="optimize case completed",
            agent_role="optimize",
            timeline_scope="child_operation",
            timeline_phase="completed",
            summary=result.summary,
            attempt_index=source_attempt_index,
            parent_operation_id=request.parent_operation_id,
            app_id=request.app_id,
            plan_id=request.plan_id,
            case_id=request.case_id,
            data={"applied": applied, "skip_reason": skip_reason},
        )
        return OptimizeCaseOperationResult(
            summary=result.summary,
            patched_fields=sorted(writeback_fields) if applied else [],
            applied=applied,
            skip_reason=skip_reason,
            confidence=confidence,
            result_path=paths["result"],
            request_path=paths["request"],
            diagnostics_path=paths["diagnostics"],
            field_diffs_path=paths["field_diffs"],
            field_diffs=[item.model_dump(mode="json") for item in field_diffs],
            artifacts=artifacts,
        )

    def execute_command(
        self,
        *,
        tracker: OperationTracker,
        request: OptimizeCaseOperationRequest,
    ) -> OperationCommandResult:
        result = self.execute(tracker=tracker, request=request)
        payload = build_optimize_case_operation_result_payload(result)
        return OperationCommandResult(
            data=payload.to_command_data(),
            artifacts=dict(result.artifacts),
            verification_verdict=None,
            result_json=payload.model_dump(mode="json"),
            status="succeeded",
        )

    @staticmethod
    def _filter_allowed_patches(
        patches: list[OptimizeFieldPatch],
        *,
        allowed_fields: set[str],
    ) -> list[OptimizeFieldPatch]:
        deduped: dict[str, OptimizeFieldPatch] = {}
        for patch in patches:
            if allowed_fields and patch.field_name not in allowed_fields:
                continue
            if patch.field_name:
                deduped[patch.field_name] = patch
        return list(deduped.values())

    @staticmethod
    def _guidance_field_items(guidance: AiGuidance, field_name: str) -> list[str]:
        value = getattr(guidance, field_name, [])
        return list(value) if isinstance(value, list) else []

    @staticmethod
    def _sanitize_guidance_items(items: list[str]) -> list[str]:
        sanitized: list[str] = []
        seen: set[str] = set()
        for raw_item in items:
            item = raw_item.strip()
            if not item:
                continue
            if len(item) > MAX_GUIDANCE_ITEM_LENGTH:
                item = item[:MAX_GUIDANCE_ITEM_LENGTH].rstrip()
            if item in seen:
                continue
            seen.add(item)
            sanitized.append(item)
            if len(sanitized) >= MAX_GUIDANCE_ITEMS_PER_FIELD:
                break
        return sanitized
