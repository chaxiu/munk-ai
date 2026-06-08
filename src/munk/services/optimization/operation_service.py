from __future__ import annotations

import json
from pathlib import Path

from munk.config import ResolvedConfig
from munk.execution.models import CaseExecutionResult
from munk.judging import JudgeResult
from munk.optimizing import OptimizeExecutionSummary, OptimizeFieldPatch, OptimizeRequest, OptimizeTrigger
from munk.planning.plan_mutation_service import PlanMutationService
from munk.planning.storage import PlanStore
from munk.services.operations.service import OperationCommandResult, OperationTracker
from munk.services.optimize_runtime import resolve_optimize_runtime
from munk.testing import AiGuidance

from .materializer import OptimizeArtifactMaterializer, OptimizeFieldDiffBundle, OptimizeFieldDiffItem
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
        case_result = CaseExecutionResult.model_validate(
            json.loads(request.result_path.read_text(encoding="utf-8"))
        )
        judge_result = self._load_judge_result(request.judge_result_path)
        trigger = request.trigger.trigger
        plan = self._plan_store.load(request.app_id, request.plan_id)
        case = next(item for item in plan.cases if item.case_id == request.case_id)
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
                source_attempt_index=request.trigger.source_attempt_index,
            ),
            artifacts=dict(case_result.artifacts),
            artifact_payloads=self._build_artifact_payloads(case_result=case_result, judge_result=judge_result),
            run_dir=request.run_dir,
        )
        paths = self._materializer.paths(run_dir=request.run_dir)
        self._materializer.write_request(paths["request"], optimize_request)
        runtime = resolve_optimize_runtime(resolved_config=self._resolved_config)
        result = runtime.optimize(optimize_request)
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
            tracker.append_event(
                event_type="optimize_case_applied",
                message="ai_guidance fields updated",
                data={"patched_fields": sorted(writeback_fields), "case_id": mutation.case.case_id},
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
        artifacts = {
            "optimization_request": str(paths["request"]),
            "optimization_result": str(paths["result"]),
            "optimization_diagnostics": str(paths["diagnostics"]),
            "field_diffs": str(paths["field_diffs"]),
        }
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
        data = {
            "summary": result.summary,
            "patched_fields": result.patched_fields,
            "applied": result.applied,
            "skip_reason": result.skip_reason,
            "confidence": result.confidence,
            "field_diffs": result.field_diffs,
            "field_diff_artifact_path": str(result.field_diffs_path),
            "optimization_result_path": str(result.result_path),
            "optimization_request_path": str(result.request_path),
            "optimization_diagnostics_path": str(result.diagnostics_path),
        }
        return OperationCommandResult(
            data=data,
            artifacts=dict(result.artifacts),
            verification_verdict=None,
            result_json={**data, "artifacts": result.artifacts},
            status="succeeded",
        )

    def _build_artifact_payloads(
        self,
        *,
        case_result: CaseExecutionResult,
        judge_result: JudgeResult | None,
    ) -> dict[str, object]:
        payloads: dict[str, object] = {}
        if judge_result is not None:
            payloads["judge_result"] = judge_result.model_dump(mode="json")
        for artifact_id in ("attempts", "history", "retry_handoffs", "decision_trace"):
            loaded = self._load_artifact_payload(case_result.artifacts.get(artifact_id))
            if loaded is not None:
                payloads[artifact_id] = loaded
        return payloads

    @staticmethod
    def _load_artifact_payload(path_value: str | None) -> object | None:
        if not path_value:
            return None
        path = Path(path_value)
        if not path.exists() or not path.is_file():
            return None
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return None
        if path.suffix == ".jsonl":
            items: list[object] = []
            for line in raw.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    return None
            return items
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

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
    def _load_judge_result(path: Path | None) -> JudgeResult | None:
        if path is None or not path.exists() or not path.is_file():
            return None
        return JudgeResult.model_validate(json.loads(path.read_text(encoding="utf-8")))

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
